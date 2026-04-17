"""
Shared database helpers: per-service SQLAlchemy engine + OpenTelemetry
instrumentation so every SQL statement produces a child span on the
current trace.

Usage (from a service app.py, AFTER create_ld_client + setup_flask_instrumentation):

    from shared.db import get_engine
    engine = get_engine(default_db='inventorydb')

The engine is auto-instrumented by `SQLAlchemyInstrumentor` so queries
appear as spans with `db.system=postgresql`, `db.statement=...`, etc.
Connection pooling is configurable via env vars to support demoing
pool-exhaustion scenarios from the payment-processor-migration flag.
"""

import os
from typing import Optional

from sqlalchemy import create_engine, Engine, event
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor


# Module-level registry so repeated get_engine() calls return the same
# engine (connection pools must not multiply).
_ENGINES: dict = {}


def get_database_url(default_db: str) -> str:
    """Resolve the DATABASE_URL for this service.

    Priority:
      1. Full DATABASE_URL env var (e.g. postgresql://user:pw@host:5432/dbname)
      2. Composed from POSTGRES_HOST/USER/PASSWORD + default_db name

    Using the composed form keeps compose files tidy — services only need
    to know their DB name, not the full connection string.
    """
    explicit = os.getenv('DATABASE_URL')
    if explicit:
        return explicit

    host = os.getenv('POSTGRES_HOST', 'postgres')
    port = os.getenv('POSTGRES_PORT', '5432')
    user = os.getenv('POSTGRES_USER', 'app')
    password = os.getenv('POSTGRES_PASSWORD', 'app')
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{default_db}"


def get_engine(
    default_db: str,
    pool_size: Optional[int] = None,
    max_overflow: Optional[int] = None,
    pool_timeout: Optional[float] = None,
    pool_pre_ping: bool = True,
) -> Engine:
    """Create (or reuse) a SQLAlchemy engine for this service, auto-instrumented for OTel.

    Args:
        default_db: Logical database name to fall back to when DATABASE_URL
                    is not set (e.g. 'inventorydb', 'orderdb').
        pool_size: Overrides SQLAlchemy default (5). Also settable via
                   DB_POOL_SIZE env var. Deliberately shrinkable so we can
                   demo connection-pool exhaustion via a feature flag.
        max_overflow: Overrides SQLAlchemy default (10). Also settable via
                      DB_MAX_OVERFLOW env var.
        pool_timeout: Seconds to wait for a free connection before raising.
                      Default 30. Also settable via DB_POOL_TIMEOUT env var.
        pool_pre_ping: Validate connections on checkout (handles stale
                       connections gracefully; small latency overhead).
    """
    url = get_database_url(default_db)
    if url in _ENGINES:
        return _ENGINES[url]

    if pool_size is None:
        pool_size = int(os.getenv('DB_POOL_SIZE', '5'))
    if max_overflow is None:
        max_overflow = int(os.getenv('DB_MAX_OVERFLOW', '10'))
    if pool_timeout is None:
        pool_timeout = float(os.getenv('DB_POOL_TIMEOUT', '30'))

    engine = create_engine(
        url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_pre_ping=pool_pre_ping,
        # echo=True would log every statement to stdout — leave off; OTel spans
        # capture db.statement already.
    )

    # Auto-instrument this engine. `enable_commenter=True` would embed trace
    # context into SQL comments for DB-side trace correlation, but Postgres
    # doesn't surface them without extensions; skip for now.
    SQLAlchemyInstrumentor().instrument(engine=engine)

    _ENGINES[url] = engine
    return engine


def install_trace_attributes(engine: Engine, service_name: str) -> None:
    """Add a small 'before_cursor_execute' hook to tag every statement
    with the service name so spans surface which service issued the query.

    OTel's SQLAlchemyInstrumentor already captures the statement; this
    just enriches it with our service label for dashboard filtering.
    """
    @event.listens_for(engine, 'before_cursor_execute')
    def _tag(conn, cursor, statement, parameters, context, executemany):  # noqa: ARG001
        try:
            from opentelemetry import trace
            span = trace.get_current_span()
            if span is not None and span.is_recording():
                span.set_attribute('app.service', service_name)
        except Exception:
            # Never let instrumentation break a query
            pass

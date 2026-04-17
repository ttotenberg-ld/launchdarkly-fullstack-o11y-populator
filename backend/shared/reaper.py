"""
Retention reaper — periodic background cleanup to keep the demo DB bounded.

Motivation
----------
The simulator writes continuously (orders, payments, chat messages, reservations).
Left unmaintained, tables grow unbounded and the demo would accumulate ~1 GB
per quarter.  This reaper runs on a schedule inside analytics-service and:

  1. DELETEs rows older than the retention window from high-volume audit tables.
     (reservations use a shorter window — they're short-lived transactional state,
      not audit history.)
  2. Restocks any `inventory` row whose stock has drifted to 0, using the
     `seed_stock` baseline.  Keeps the demo from permanently running out.
  3. Holds a Postgres advisory lock so parallel analytics-service replicas
     won't double-sweep.

The reaper is intentionally logged and span-instrumented — a retention.sweep
span appears in traces every 5 minutes, which doubles as a liveness signal.
"""

import os
from typing import Dict

from sqlalchemy import text

from ldobserve.observe import record_log, record_exception, start_span, LEVELS

from shared.db import get_engine


# Retention windows (seconds) — overridable via env for debugging.
RETENTION_SECONDS_DEFAULT = int(os.getenv('RETENTION_SECONDS', 7 * 24 * 3600))  # 7 days
RETENTION_SECONDS_RESERVATIONS = int(os.getenv('RETENTION_SECONDS_RESERVATIONS', 2 * 3600))  # 2 hours

# Advisory lock ID — arbitrary constant shared across all reaper replicas.
_REAPER_LOCK_ID = 773311


def _delete_old(conn, table: str, ts_col: str, retention_seconds: int) -> int:
    """DELETE rows older than retention_seconds; return deleted row count."""
    result = conn.execute(
        text(f"""
            DELETE FROM {table}
            WHERE {ts_col} < NOW() - (:seconds * INTERVAL '1 second')
        """),
        {'seconds': retention_seconds},
    )
    return result.rowcount or 0


def _sweep_paymentdb(retention_seconds: int) -> Dict[str, int]:
    engine = get_engine(default_db='paymentdb')
    counts: Dict[str, int] = {}
    with engine.begin() as conn:
        # refunds first — FK to payments would block otherwise.
        counts['refunds'] = _delete_old(conn, 'refunds', 'created_at', retention_seconds)
        counts['payments'] = _delete_old(conn, 'payments', 'created_at', retention_seconds)
    return counts


def _sweep_orderdb(retention_seconds: int) -> Dict[str, int]:
    engine = get_engine(default_db='orderdb')
    counts: Dict[str, int] = {}
    with engine.begin() as conn:
        # orders CASCADEs to order_items on delete.
        counts['orders'] = _delete_old(conn, 'orders', 'created_at', retention_seconds)
    return counts


def _sweep_chatdb(retention_seconds: int) -> Dict[str, int]:
    engine = get_engine(default_db='chatdb')
    counts: Dict[str, int] = {}
    with engine.begin() as conn:
        # conversations CASCADEs to messages. Key on last_msg_at so active
        # conversations older than 7d but still receiving messages survive.
        counts['conversations'] = _delete_old(conn, 'conversations', 'last_msg_at', retention_seconds)
        counts['chat_feedback'] = _delete_old(conn, 'chat_feedback', 'created_at', retention_seconds)
    return counts


def _sweep_inventorydb(reservations_retention_seconds: int) -> Dict[str, int]:
    """Short-retention sweep for reservations + inventory restock."""
    engine = get_engine(default_db='inventorydb')
    counts: Dict[str, int] = {}
    with engine.begin() as conn:
        counts['reservations'] = _delete_old(
            conn, 'reservations', 'created_at', reservations_retention_seconds,
        )
        # Restock anything that's drifted to 0. Idempotent — products above 0
        # are untouched, so we don't interfere with in-flight reservations.
        result = conn.execute(
            text("""
                UPDATE inventory
                SET stock = seed_stock,
                    reserved = 0,
                    updated_at = NOW()
                WHERE stock = 0
                RETURNING product_id
            """),
        )
        restocked = result.fetchall()
        counts['inventory_restocked'] = len(restocked)
        if restocked:
            record_log(
                f"Restocked {len(restocked)} products: "
                + ', '.join(r.product_id for r in restocked),
                LEVELS['info'],
                {'service': 'analytics-service', 'reaper.stage': 'inventory_restock'},
            )
    return counts


def run_retention_sweep(
    retention_seconds: int = RETENTION_SECONDS_DEFAULT,
    reservations_retention_seconds: int = RETENTION_SECONDS_RESERVATIONS,
) -> Dict[str, int]:
    """Execute a single retention pass. Safe to call concurrently — uses an
    advisory lock so only one instance sweeps at a time.

    Returns a dict mapping table -> deleted row count (plus inventory_restocked).
    """
    with start_span('retention.sweep') as span:
        span.set_attribute('reaper.retention_seconds', retention_seconds)
        span.set_attribute('reaper.reservations_retention_seconds', reservations_retention_seconds)

        # Advisory lock — acquired on any one DB; unlock on exit. Using a
        # session-level lock so it auto-releases if the process dies.
        lock_engine = get_engine(default_db='paymentdb')
        with lock_engine.connect() as lock_conn:
            acquired = lock_conn.execute(
                text("SELECT pg_try_advisory_lock(:id)"),
                {'id': _REAPER_LOCK_ID},
            ).scalar()
            if not acquired:
                span.set_attribute('reaper.skipped', True)
                span.set_attribute('reaper.skip_reason', 'lock_not_acquired')
                record_log(
                    "Retention sweep skipped: another instance holds the lock",
                    LEVELS['debug'],
                    {'service': 'analytics-service', 'reaper.stage': 'lock'},
                )
                return {'skipped': 1}

            try:
                results: Dict[str, int] = {}
                for sweep_name, sweep_fn in [
                    ('paymentdb', lambda: _sweep_paymentdb(retention_seconds)),
                    ('orderdb', lambda: _sweep_orderdb(retention_seconds)),
                    ('chatdb', lambda: _sweep_chatdb(retention_seconds)),
                    ('inventorydb', lambda: _sweep_inventorydb(reservations_retention_seconds)),
                ]:
                    try:
                        results.update(sweep_fn())
                    except Exception as e:
                        record_exception(e, {
                            'service': 'analytics-service',
                            'reaper.stage': sweep_name,
                        })

                total_deleted = sum(v for k, v in results.items() if k != 'inventory_restocked')
                span.set_attribute('reaper.total_deleted', total_deleted)
                span.set_attribute('reaper.inventory_restocked', results.get('inventory_restocked', 0))
                for table, count in results.items():
                    span.set_attribute(f'reaper.count.{table}', count)

                record_log(
                    f"Retention sweep complete: {total_deleted} rows deleted, "
                    f"{results.get('inventory_restocked', 0)} products restocked",
                    LEVELS['info'],
                    {
                        'service': 'analytics-service',
                        'reaper.stage': 'complete',
                        **{f'reaper.count.{k}': v for k, v in results.items()},
                    },
                )
                return results
            finally:
                lock_conn.execute(
                    text("SELECT pg_advisory_unlock(:id)"),
                    {'id': _REAPER_LOCK_ID},
                )

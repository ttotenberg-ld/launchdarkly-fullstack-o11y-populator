"""
Payment Service - Payment processing and validation.
Port: 5004
"""

import os
import time
import uuid
import random
import requests
from typing import Optional
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

from ldclient import Context
from ldobserve.observe import (
    record_log,
    record_exception,
    start_span,
    record_count,
    record_histogram,
    LEVELS,
)

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from shared.observability import (
    create_ld_client,
    get_common_attributes,
    setup_flask_instrumentation,
    build_service_context,
)
from shared.db import get_engine, install_trace_attributes

from shared.service_names import get_service_url
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

# Load environment variables
load_dotenv()

# Service configuration
SERVICE_NAME = os.getenv('SERVICE_NAME', 'payment-service')
SERVICE_VERSION = os.getenv('SERVICE_VERSION', '1.0.0')
USE_DOCKER = os.getenv('USE_DOCKER', 'true').lower() == 'true'

# IMPORTANT: Initialize LaunchDarkly FIRST to set up tracer provider
client = create_ld_client(SERVICE_NAME, SERVICE_VERSION)

# Initialize Flask app
app = Flask(__name__)
CORS(app, expose_headers=['traceparent', 'tracestate'], allow_headers=['Content-Type', 'traceparent', 'tracestate'])

# Set up instrumentation AFTER LD client is initialized
setup_flask_instrumentation(app)

# Database engine — pool size tunable via env so payment-processor-migration v2
# can demo pool exhaustion without a code change.
_pool_size = int(os.getenv('PAYMENT_DB_POOL_SIZE', '5'))
_max_overflow = int(os.getenv('PAYMENT_DB_MAX_OVERFLOW', '10'))
engine = get_engine(
    default_db='paymentdb',
    pool_size=_pool_size,
    max_overflow=_max_overflow,
)
install_trace_attributes(engine, SERVICE_NAME)


USER_HEADERS = ['X-User-Key', 'X-User-Name', 'X-User-Email', 'X-User-Plan', 'X-User-Role', 'X-User-Metro', 'X-User-Country']


# ============================================================================
# FLAG: payment-processor-migration
# ============================================================================
# Multivariate string flag (default "v1"):
#   v1 — legacy stable processor. Clean baseline.
#   v2 — in-flight migration: injects DB pathologies (slow queries, planner
#        regressions, transaction rollbacks, pool pressure) so traces surface
#        the cost of the migration.
#   v3 — migration complete. Same code path as v1; acts as the "success"
#        variation for comparing before/after in dashboards.
FLAG_KEY_PROCESSOR = "payment-processor-migration"


class PaymentProcessorError(Exception):
    """Raised when a simulated pathology fires. Surfaces as a 500 via the
    global error handler so traces, logs, and metrics all see the failure."""

    def __init__(self, message: str, error_type: str, status_code: int = 500):
        super().__init__(message)
        self.error_type = error_type
        self.status_code = status_code


def _build_user_context() -> Optional[Context]:
    """Extract user context from X-User-* headers, or None on health checks."""
    user_key = request.headers.get('X-User-Key')
    if not user_key:
        return None
    builder = Context.builder(user_key).kind("user")
    name = request.headers.get('X-User-Name')
    if name:
        builder.name(name)
    for header, attr in [
        ('X-User-Email', 'email'),
        ('X-User-Plan', 'plan'),
        ('X-User-Role', 'role'),
        ('X-User-Metro', 'metro'),
        ('X-User-Country', 'country'),
    ]:
        value = request.headers.get(header)
        if value:
            builder.set(attr, value)
    return builder.build()


def build_evaluation_context() -> Context:
    """Multi-context: user (if present) + request (ephemeral) + service (stable)."""
    user_context = _build_user_context()
    request_context = Context.builder(str(uuid.uuid4())) \
        .kind("request") \
        .set("timestamp", time.time()) \
        .set("endpoint", request.path) \
        .set("method", request.method) \
        .set("anonymous", True) \
        .build()
    service_context = build_service_context(SERVICE_NAME)
    if user_context:
        return Context.create_multi(user_context, request_context, service_context)
    return Context.create_multi(request_context, service_context)


def get_processor_version() -> str:
    """Evaluate payment-processor-migration and return 'v1' | 'v2' | 'v3'."""
    context = build_evaluation_context()
    detail = client.variation_detail(FLAG_KEY_PROCESSOR, context, "v1")
    value = detail.value if detail.value in ("v1", "v2", "v3") else "v1"
    record_log(
        f"Flag '{FLAG_KEY_PROCESSOR}' evaluated to {value}",
        LEVELS['info'],
        {
            **get_common_attributes(SERVICE_NAME, request.path),
            'flag.key': FLAG_KEY_PROCESSOR,
            'flag.value': value,
            'flag.variation_index': detail.variation_index,
            'flag.reason.kind': (detail.reason or {}).get('kind', 'unknown'),
        },
    )
    return value


# v2 pathology scenarios. Each fires probabilistically on a /process request
# that resolves to v2, producing distinct trace-visible failure modes.
PAYMENT_V2_PATHOLOGIES = [
    {
        "kind": "slow_query",
        "rate": 0.30,
        "description": "pg_sleep-induced slow query before INSERT",
    },
    {
        "kind": "seq_scan_regression",
        "rate": 0.20,
        "description": "ORDER BY a function of created_at — planner ignores the index",
    },
    {
        "kind": "pool_hold",
        "rate": 0.10,
        "description": "Holds a checked-out connection open to pressure the pool",
    },
    {
        "kind": "rollback",
        "rate": 0.08,
        "description": "Forces ROLLBACK after INSERT to simulate a failed commit path",
    },
]


def _pick_v2_pathology() -> Optional[dict]:
    """Return a single pathology scenario, or None for a clean v2 request."""
    roll = random.random()
    cumulative = 0.0
    for scenario in PAYMENT_V2_PATHOLOGIES:
        cumulative += scenario["rate"]
        if roll < cumulative:
            return scenario
    return None


def _run_pathology(scenario: dict, conn) -> None:
    """Execute the pathology against an open connection. Called inside the
    transaction so BEGIN/query/ROLLBACK all show up as child spans."""
    kind = scenario["kind"]
    if kind == "slow_query":
        delay = round(random.uniform(1.5, 3.5), 2)
        conn.execute(text("SELECT pg_sleep(:d)"), {'d': delay})
    elif kind == "seq_scan_regression":
        # `LOWER(order_id)` is a function of an indexed column — no functional
        # index exists, so Postgres falls back to a seq scan.
        conn.execute(text("""
            SELECT id, amount_cents
            FROM payments
            WHERE LOWER(order_id) LIKE :p
            ORDER BY LOWER(order_id) DESC
            LIMIT 50
        """), {'p': '%seed%'})
    elif kind == "pool_hold":
        # Holds the connection ~2.5s — combined with the default pool size of
        # 5 + 10 overflow, concurrent bursts from the simulator will hit
        # QueuePool timeouts, which surface as SQLAlchemy TimeoutError spans.
        conn.execute(text("SELECT pg_sleep(2.5)"))
    elif kind == "rollback":
        # Raise *inside* the transaction so the engine.begin() block fires a
        # ROLLBACK — visible as a distinct trace event from a clean COMMIT.
        raise PaymentProcessorError(
            "Payment processor v2: post-insert validation failed, rolling back",
            error_type="PaymentProcessorV2RollbackError",
            status_code=500,
        )


def get_trace_headers():
    """Extract trace context and user context headers from the incoming request."""
    headers = {}
    for key in ['traceparent', 'tracestate'] + USER_HEADERS:
        if key in request.headers:
            headers[key] = request.headers[key]
    return headers


def call_service(service_name: str, path: str, method: str = 'GET', data: dict = None) -> dict:
    """Call a downstream service."""
    url = get_service_url(service_name, USE_DOCKER) + path
    headers = get_trace_headers()
    headers['Content-Type'] = 'application/json'
    
    try:
        if method == 'POST':
            resp = requests.post(url, json=data, headers=headers, timeout=30)
        else:
            resp = requests.get(url, headers=headers, timeout=30)
        return resp.json()
    except requests.exceptions.RequestException as e:
        record_exception(e, {
            **get_common_attributes(SERVICE_NAME, path),
            'downstream_service': service_name,
        })
        raise


# Global error handler
@app.errorhandler(Exception)
def handle_exception(error):
    """Global error handler."""
    status_code = getattr(error, 'status_code', 500)
    error_type = getattr(error, 'error_type', type(error).__name__)
    
    record_exception(error, {
        **get_common_attributes(SERVICE_NAME, request.path),
        'error_type': error_type,
    })
    
    return jsonify({
        'success': False,
        'error': error_type,
        'message': str(error),
        'service': SERVICE_NAME,
    }), status_code


# ============================================================================
# PAYMENT ROUTES
# ============================================================================

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': SERVICE_NAME,
        'version': SERVICE_VERSION,
    })


@app.route('/process', methods=['POST'])
def process_payment():
    """Process a payment."""
    with start_span('payment.process') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)

        data = request.get_json() or {}
        order_id = data.get('order_id', f"ord_{uuid.uuid4().hex[:12]}")
        amount = data.get('amount', random.uniform(20, 200))
        currency = data.get('currency', 'USD')
        user = data.get('user', {})

        transaction_id = f"txn_{uuid.uuid4().hex[:12]}"
        processor_version = get_processor_version()

        span.set_attribute('order_id', order_id)
        span.set_attribute('amount', amount)
        span.set_attribute('currency', currency)
        span.set_attribute('transaction_id', transaction_id)
        span.set_attribute('processor_version', processor_version)

        record_log(f"Processing payment for order {order_id}", LEVELS['info'], {
            **get_common_attributes(SERVICE_NAME, '/process'),
            'order_id': order_id,
            'amount': amount,
            'currency': currency,
            'provider': 'stripe',
            'processor_version': processor_version,
        })

        # Step 1: Validate card
        with start_span('payment.validate_card') as val_span:
            val_span.set_attribute('service', SERVICE_NAME)
            val_span.set_attribute('step', 'validate_card')

            # Simulate card validation
            time.sleep(0.3)
            val_span.set_attribute('card.valid', True)

        # Step 2: Fraud check
        with start_span('payment.fraud_check') as fraud_span:
            fraud_span.set_attribute('service', SERVICE_NAME)
            fraud_span.set_attribute('step', 'fraud_check')

            # Simulate fraud detection
            time.sleep(0.2)
            fraud_score = round(random.uniform(0, 0.3), 3)  # Low risk; 3 decimals fits NUMERIC(4,3)
            fraud_span.set_attribute('fraud_score', fraud_score)

            record_log(f"Fraud check passed for transaction {transaction_id}", LEVELS['debug'], {
                **get_common_attributes(SERVICE_NAME, '/process'),
                'transaction_id': transaction_id,
                'fraud_score': fraud_score,
            })

        # Step 3: Charge card
        with start_span('payment.charge') as charge_span:
            charge_span.set_attribute('service', SERVICE_NAME)
            charge_span.set_attribute('step', 'charge')

            # Simulate payment gateway call
            time.sleep(0.4)
            charge_span.set_attribute('charge.success', True)

        # Persist payment row transactionally — BEGIN/INSERT/COMMIT show up as
        # child spans of payment.process thanks to SQLAlchemy instrumentation.
        amount_cents = int(round(float(amount) * 100))
        user_plan = (user or {}).get('plan', 'unknown')

        # Pick a v2 pathology before opening the transaction so the choice
        # is visible on the parent span even if the request fails later.
        v2_scenario = _pick_v2_pathology() if processor_version == 'v2' else None
        if v2_scenario:
            span.set_attribute('payment.pathology.kind', v2_scenario['kind'])

        with start_span('payment.persist') as persist_span:
            persist_span.set_attribute('service', SERVICE_NAME)
            persist_span.set_attribute('processor_version', processor_version)
            if v2_scenario:
                persist_span.set_attribute('pathology.kind', v2_scenario['kind'])
            try:
                with engine.begin() as conn:
                    # Slow query / seq scan regressions fire *before* the INSERT
                    # so the INSERT itself stays fast — matches real-world
                    # "background query slowed the whole path" patterns.
                    if v2_scenario and v2_scenario['kind'] in ('slow_query', 'seq_scan_regression', 'pool_hold'):
                        _run_pathology(v2_scenario, conn)

                    conn.execute(
                        text("""
                            INSERT INTO payments (
                                id, order_id, amount_cents, currency, status, provider,
                                fraud_score, processor_version, user_plan, completed_at
                            ) VALUES (
                                :id, :order_id, :amount_cents, :currency, 'completed', 'stripe',
                                :fraud_score, :processor_version, :user_plan, NOW()
                            )
                        """),
                        {
                            'id': transaction_id,
                            'order_id': order_id,
                            'amount_cents': amount_cents,
                            'currency': currency,
                            'fraud_score': fraud_score,
                            'processor_version': processor_version,
                            'user_plan': user_plan,
                        },
                    )

                    # Rollback pathology fires *after* the INSERT so the ROLLBACK
                    # span is the smoking gun — INSERT succeeded, commit didn't.
                    if v2_scenario and v2_scenario['kind'] == 'rollback':
                        _run_pathology(v2_scenario, conn)
            except PaymentProcessorError:
                # Bubble to the global handler so it surfaces as a 5xx with
                # the right error_type on the trace.
                record_count('app.payment.processed_total', 1, {
                    'success': 'false',
                    'currency': currency,
                    'user_plan': user_plan,
                    'processor_version': processor_version,
                    'pathology': v2_scenario['kind'] if v2_scenario else 'none',
                })
                raise
            except SQLAlchemyError as db_err:
                # Pool timeouts, operational errors, etc. Record and re-raise
                # so the global handler returns the standard error payload.
                record_exception(db_err, {
                    **get_common_attributes(SERVICE_NAME, '/process'),
                    'processor_version': processor_version,
                    'pathology': v2_scenario['kind'] if v2_scenario else 'none',
                })
                record_count('app.payment.processed_total', 1, {
                    'success': 'false',
                    'currency': currency,
                    'user_plan': user_plan,
                    'processor_version': processor_version,
                    'pathology': v2_scenario['kind'] if v2_scenario else 'none',
                })
                raise

        record_log(f"Payment successful for order {order_id}", LEVELS['info'], {
            **get_common_attributes(SERVICE_NAME, '/process'),
            'order_id': order_id,
            'transaction_id': transaction_id,
            'amount': amount,
            'status': 'completed',
        })

        # Bucket the amount for dimensional analysis without blowing up cardinality.
        if amount < 50:
            amount_bucket = '0-50'
        elif amount < 100:
            amount_bucket = '50-100'
        elif amount < 200:
            amount_bucket = '100-200'
        else:
            amount_bucket = '200+'

        record_count('app.payment.processed_total', 1, {
            'success': 'true',
            'currency': currency,
            'amount_bucket': amount_bucket,
            'user_plan': user_plan,
            'processor_version': processor_version,
            'pathology': v2_scenario['kind'] if v2_scenario else 'none',
        })
        record_histogram('app.payment.amount_usd', float(amount), {
            'currency': currency,
            'user_plan': user_plan,
            'processor_version': processor_version,
        })
        
        # Send receipt notification
        try:
            call_service('notification-service', '/send', 'POST', {
                'type': 'email',
                'template': 'payment_receipt',
                'user': user,
                'transaction_id': transaction_id,
                'amount': amount,
            })
        except Exception as e:
            record_log(f"Failed to send payment receipt: {e}", LEVELS['error'],
                       get_common_attributes(SERVICE_NAME, '/process'))
        
        return jsonify({
            'success': True,
            'service': SERVICE_NAME,
            'transaction': {
                'id': transaction_id,
                'order_id': order_id,
                'amount': amount,
                'currency': currency,
                'status': 'completed',
                'provider': 'stripe',
            }
        })


@app.route('/refund', methods=['POST'])
def refund_payment():
    """Process a refund."""
    with start_span('payment.refund') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)

        data = request.get_json() or {}
        transaction_id = data.get('transaction_id', f"txn_{uuid.uuid4().hex[:12]}")
        amount = data.get('amount', random.uniform(20, 200))

        refund_id = f"ref_{uuid.uuid4().hex[:12]}"
        amount_cents = int(round(float(amount) * 100))

        span.set_attribute('transaction_id', transaction_id)
        span.set_attribute('refund_id', refund_id)
        span.set_attribute('amount', amount)

        # Simulate refund processing
        time.sleep(0.5)

        # Transactional insert — if the referenced payment doesn't exist (e.g.
        # a stale transaction_id from the simulator), the FK check will fail
        # and we surface a 404-ish error rather than ghost-writing a refund.
        try:
            with engine.begin() as conn:
                exists = conn.execute(
                    text("SELECT 1 FROM payments WHERE id = :id"),
                    {'id': transaction_id},
                ).first()
                if not exists:
                    span.set_attribute('refund.payment_found', False)
                    return jsonify({
                        'success': False,
                        'service': SERVICE_NAME,
                        'error': 'PaymentNotFound',
                        'message': f"No payment with id {transaction_id}",
                    }), 404

                conn.execute(
                    text("""
                        INSERT INTO refunds (id, payment_id, amount_cents, status)
                        VALUES (:id, :payment_id, :amount_cents, 'completed')
                    """),
                    {
                        'id': refund_id,
                        'payment_id': transaction_id,
                        'amount_cents': amount_cents,
                    },
                )
        except Exception as e:
            record_exception(e, {
                **get_common_attributes(SERVICE_NAME, '/refund'),
                'transaction_id': transaction_id,
                'refund_id': refund_id,
            })
            raise

        record_log(f"Refund processed for transaction {transaction_id}", LEVELS['info'], {
            **get_common_attributes(SERVICE_NAME, '/refund'),
            'transaction_id': transaction_id,
            'refund_id': refund_id,
            'amount': amount,
        })

        return jsonify({
            'success': True,
            'service': SERVICE_NAME,
            'refund': {
                'id': refund_id,
                'transaction_id': transaction_id,
                'amount': amount,
                'status': 'completed',
            }
        })


@app.route('/balance', methods=['GET'])
def get_balance():
    """Get account balance — aggregated from the payments/refunds tables."""
    with start_span('payment.balance') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)

        with engine.connect() as conn:
            # Completed payments minus refunds = available balance.
            # Pending payments = still in-flight (status='pending').
            row = conn.execute(text("""
                SELECT
                    COALESCE(SUM(CASE WHEN status = 'completed' THEN amount_cents ELSE 0 END), 0) AS completed_cents,
                    COALESCE(SUM(CASE WHEN status = 'pending'   THEN amount_cents ELSE 0 END), 0) AS pending_cents
                FROM payments
            """)).first()
            refunded_row = conn.execute(text("""
                SELECT COALESCE(SUM(amount_cents), 0) AS refunded_cents
                FROM refunds
                WHERE status = 'completed'
            """)).first()

        completed_cents = int(row.completed_cents or 0)
        pending_cents = int(row.pending_cents or 0)
        refunded_cents = int(refunded_row.refunded_cents or 0)
        available_cents = completed_cents - refunded_cents

        span.set_attribute('balance.completed_cents', completed_cents)
        span.set_attribute('balance.refunded_cents', refunded_cents)
        span.set_attribute('balance.pending_cents', pending_cents)

        return jsonify({
            'success': True,
            'service': SERVICE_NAME,
            'balance': {
                'available': round(available_cents / 100, 2),
                'pending': round(pending_cents / 100, 2),
                'currency': 'USD',
            }
        })


@app.route('/', methods=['GET'])
def root():
    """Root endpoint."""
    return jsonify({
        'service': SERVICE_NAME,
        'version': SERVICE_VERSION,
        'endpoints': ['/health', '/process', '/refund', '/balance']
    })


if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5004))
    print(f"\n🚀 Starting {SERVICE_NAME} on http://localhost:{port}")
    app.run(debug=False, host='0.0.0.0', port=port)

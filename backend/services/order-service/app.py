"""
Order Service - Order processing, checkout flow.
Port: 5003
"""

import os
import time
import uuid
import random
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

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

from shared.observability import create_ld_client, get_common_attributes, setup_flask_instrumentation
from shared.db import get_engine, install_trace_attributes
from shared.users import get_random_user

from shared.service_names import get_service_url
from sqlalchemy import text

# Load environment variables
load_dotenv()

# Service configuration
SERVICE_NAME = os.getenv('SERVICE_NAME', 'order-service')
SERVICE_VERSION = os.getenv('SERVICE_VERSION', '1.0.0')
USE_DOCKER = os.getenv('USE_DOCKER', 'true').lower() == 'true'

# IMPORTANT: Initialize LaunchDarkly FIRST to set up tracer provider
client = create_ld_client(SERVICE_NAME, SERVICE_VERSION)

# Initialize Flask app
app = Flask(__name__)
CORS(app, expose_headers=['traceparent', 'tracestate'], allow_headers=['Content-Type', 'traceparent', 'tracestate'])

# Set up instrumentation AFTER LD client is initialized
setup_flask_instrumentation(app)

# Postgres engine (auto-instrumented: every SQL statement becomes a span).
engine = get_engine(default_db='orderdb')
install_trace_attributes(engine, SERVICE_NAME)

# Small in-memory fallback catalogue used only when checkout is called
# without explicit items (sparingly, for demo paths).
PRODUCTS = [
    {'id': 'prod_001', 'name': 'Feature Flag Starter Kit', 'price': 29.99},
    {'id': 'prod_002', 'name': 'Progressive Rollout Pro', 'price': 49.99},
    {'id': 'prod_003', 'name': 'A/B Testing Suite', 'price': 79.99},
    {'id': 'prod_004', 'name': 'Targeting Rules Package', 'price': 39.99},
    {'id': 'prod_005', 'name': 'Segment Builder', 'price': 59.99},
]


USER_HEADERS = ['X-User-Key', 'X-User-Name', 'X-User-Email', 'X-User-Plan', 'X-User-Role', 'X-User-Metro', 'X-User-Country']

def get_trace_headers():
    """Extract trace context and user context headers."""
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
# ORDER ROUTES
# ============================================================================

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': SERVICE_NAME,
        'version': SERVICE_VERSION,
    })


@app.route('/checkout', methods=['POST'])
def checkout():
    """Process checkout - the main multi-service flow."""
    with start_span('order.checkout') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)
        
        data = request.get_json() or {}
        user = data.get('user', get_random_user())
        items = data.get('items', random.sample(PRODUCTS, k=random.randint(1, 3)))

        # Frontend-supplied flag variants (the variant the user actually saw
        # at checkout time).  Used to tag business metrics so flag impact on
        # revenue/funnel is attributable in LD.
        layout_variant = data.get('layout_variant', 'unknown')
        promo_variant = data.get('promo_variant', 'unknown')

        order_id = f"ord_{uuid.uuid4().hex[:12]}"
        total = sum(item.get('price', 0) for item in items)
        total_cents = int(round(total * 100))

        span.set_attribute('order_id', order_id)
        span.set_attribute('item_count', len(items))
        span.set_attribute('total', total)
        span.set_attribute('layout_variant', layout_variant)
        span.set_attribute('promo_variant', promo_variant)

        # Persist the pending order BEFORE downstream calls, so even failed
        # checkouts produce an auditable row (and a BEGIN/INSERT/COMMIT
        # span tree at the top of the trace).
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO orders "
                    "  (id, user_key, user_email, user_plan, layout_variant, "
                    "   promo_variant, total_cents, status) "
                    "VALUES (:id, :uk, :ue, :up, :lv, :pv, :tc, 'pending')"
                ),
                {
                    'id': order_id,
                    'uk': (user or {}).get('key', 'unknown'),
                    'ue': (user or {}).get('email'),
                    'up': (user or {}).get('plan', 'unknown'),
                    'lv': layout_variant,
                    'pv': promo_variant,
                    'tc': total_cents,
                },
            )
            for item in items:
                conn.execute(
                    text(
                        "INSERT INTO order_items "
                        "  (order_id, product_id, product_name, quantity, price_cents) "
                        "VALUES (:oid, :pid, :pname, :qty, :pc)"
                    ),
                    {
                        'oid': order_id,
                        'pid': item.get('id'),
                        'pname': item.get('name'),
                        'qty': int(item.get('quantity', 1)),
                        'pc': int(round(float(item.get('price', 0)) * 100)),
                    },
                )

        # Common attributes applied to every business metric for this order,
        # so flag variants are attributable downstream.
        metric_attrs = {
            'layout_variant': layout_variant,
            'promo_variant': promo_variant,
            'user_plan': (user or {}).get('plan', 'unknown'),
        }
        
        record_log(f"Processing checkout for order {order_id}", LEVELS['info'], {
            **get_common_attributes(SERVICE_NAME, '/checkout'),
            'order_id': order_id,
            'user_email': user['email'],
            'item_count': len(items),
            'total': total,
        })
        
        # Step 1: Reserve inventory
        with start_span('order.checkout.reserve_inventory') as inv_span:
            inv_span.set_attribute('service', SERVICE_NAME)
            inv_span.set_attribute('step', 'reserve_inventory')
            
            record_log(f"Reserving inventory for order {order_id}", LEVELS['info'], {
                **get_common_attributes(SERVICE_NAME, '/checkout'),
                'order_id': order_id,
                'step': 'reserve_inventory',
            })
            
            try:
                inventory_result = call_service('inventory-service', '/reserve', 'POST', {
                    'order_id': order_id,
                    'items': [{'product_id': item['id'], 'quantity': 1} for item in items],
                })
                inv_span.set_attribute('reservation.success', inventory_result.get('success', False))
                record_count('app.checkout.funnel_step_total', 1, {
                    **metric_attrs,
                    'step': 'reserve_inventory',
                    'success': 'true',
                })
            except Exception as e:
                record_count('app.checkout.funnel_step_total', 1, {
                    **metric_attrs,
                    'step': 'reserve_inventory',
                    'success': 'false',
                })
                record_log(f"Inventory reservation failed for order {order_id}: {e}", LEVELS['error'], {
                    **get_common_attributes(SERVICE_NAME, '/checkout'),
                    'order_id': order_id,
                    'step': 'reserve_inventory',
                    'error': str(e),
                })
                raise
        
        # Step 2: Process payment
        with start_span('order.checkout.process_payment') as pay_span:
            pay_span.set_attribute('service', SERVICE_NAME)
            pay_span.set_attribute('step', 'process_payment')
            
            record_log(f"Processing payment for order {order_id}", LEVELS['info'], {
                **get_common_attributes(SERVICE_NAME, '/checkout'),
                'order_id': order_id,
                'step': 'process_payment',
                'amount': total,
            })
            
            try:
                payment_result = call_service('payment-service', '/process', 'POST', {
                    'order_id': order_id,
                    'amount': total,
                    'currency': 'USD',
                    'user': user,
                })
                pay_span.set_attribute('payment.success', payment_result.get('success', False))
                record_count('app.checkout.funnel_step_total', 1, {
                    **metric_attrs,
                    'step': 'process_payment',
                    'success': 'true',
                })
            except Exception as e:
                record_count('app.checkout.funnel_step_total', 1, {
                    **metric_attrs,
                    'step': 'process_payment',
                    'success': 'false',
                })
                record_log(f"Payment processing failed for order {order_id}: {e}", LEVELS['error'], {
                    **get_common_attributes(SERVICE_NAME, '/checkout'),
                    'order_id': order_id,
                    'step': 'process_payment',
                    'error': str(e),
                })
                raise
        
        # Step 3: Send confirmation
        with start_span('order.checkout.send_notification') as notif_span:
            notif_span.set_attribute('service', SERVICE_NAME)
            notif_span.set_attribute('step', 'send_notification')
            
            try:
                call_service('notification-service', '/send', 'POST', {
                    'type': 'email',
                    'template': 'order_confirmation',
                    'user': user,
                    'order_id': order_id,
                    'total': total,
                })
            except Exception as e:
                # Non-critical - log but don't fail the order
                record_log(f"Failed to send order confirmation: {e}", LEVELS['error'], {
                    **get_common_attributes(SERVICE_NAME, '/checkout'),
                    'order_id': order_id,
                })
        
        # Mark the order complete in the DB (UPDATE span on the trace)
        with engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE orders SET status = 'completed', completed_at = NOW() "
                    "WHERE id = :id"
                ),
                {'id': order_id},
            )

        record_log(f"Order {order_id} completed successfully", LEVELS['info'], {
            **get_common_attributes(SERVICE_NAME, '/checkout'),
            'order_id': order_id,
            'total': total,
            'status': 'completed',
        })

        # Revenue metrics — the core business outcomes.  Tagged with the
        # flag variants the user saw so you can correlate flag state with
        # orders and revenue in LD.
        record_count('app.order.placed_total', 1, {
            **metric_attrs,
            'item_count': str(len(items)),
        })
        record_histogram('app.order.value_usd', float(total), metric_attrs)
        
        return jsonify({
            'success': True,
            'service': SERVICE_NAME,
            'order': {
                'id': order_id,
                'status': 'completed',
                'items': items,
                'total': total,
                'user': user,
            }
        })


@app.route('/orders', methods=['GET'])
def list_orders():
    """List recent orders (reads from orderdb — two-query pattern: orders
    then line-items per order, which produces a visible N+1 shape in the
    trace when N grows.  Kept simple deliberately — realism > perfection.)"""
    with start_span('order.list') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)

        limit = int(request.args.get('limit', 10))

        with engine.connect() as conn:
            order_rows = conn.execute(
                text(
                    "SELECT id, user_key, user_email, user_plan, total_cents, "
                    "       status, created_at, completed_at "
                    "FROM orders ORDER BY created_at DESC LIMIT :lim"
                ),
                {'lim': limit},
            ).fetchall()

            orders = []
            for row in order_rows:
                item_rows = conn.execute(
                    text(
                        "SELECT product_id, product_name, quantity, price_cents "
                        "FROM order_items WHERE order_id = :oid"
                    ),
                    {'oid': row.id},
                ).fetchall()
                orders.append({
                    'id': row.id,
                    'user': {
                        'key': row.user_key,
                        'email': row.user_email,
                        'plan': row.user_plan,
                    },
                    'items': [
                        {
                            'id': ir.product_id,
                            'name': ir.product_name,
                            'quantity': ir.quantity,
                            'price': (ir.price_cents or 0) / 100.0,
                        }
                        for ir in item_rows
                    ],
                    'total': (row.total_cents or 0) / 100.0,
                    'status': row.status,
                    'created_at': row.created_at.isoformat() if row.created_at else None,
                })

        record_log(f"Retrieved {len(orders)} orders", LEVELS['info'],
                   get_common_attributes(SERVICE_NAME, '/orders'))

        return jsonify({
            'success': True,
            'service': SERVICE_NAME,
            'orders': orders,
        })


@app.route('/orders/<order_id>', methods=['GET'])
def get_order(order_id):
    """Get order details from orderdb."""
    with start_span('order.get') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)
        span.set_attribute('order_id', order_id)

        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT id, user_key, user_email, user_plan, total_cents, "
                    "       status, created_at, completed_at "
                    "FROM orders WHERE id = :oid"
                ),
                {'oid': order_id},
            ).fetchone()

            if not row:
                return jsonify({
                    'success': False,
                    'error': 'OrderNotFound',
                    'message': f'Order {order_id} not found',
                }), 404

            item_rows = conn.execute(
                text(
                    "SELECT product_id, product_name, quantity, price_cents "
                    "FROM order_items WHERE order_id = :oid"
                ),
                {'oid': order_id},
            ).fetchall()

        return jsonify({
            'success': True,
            'service': SERVICE_NAME,
            'order': {
                'id': row.id,
                'user': {
                    'key': row.user_key,
                    'email': row.user_email,
                    'plan': row.user_plan,
                },
                'items': [
                    {
                        'id': ir.product_id,
                        'name': ir.product_name,
                        'quantity': ir.quantity,
                        'price': (ir.price_cents or 0) / 100.0,
                    }
                    for ir in item_rows
                ],
                'total': (row.total_cents or 0) / 100.0,
                'status': row.status,
            }
        })


@app.route('/', methods=['GET'])
def root():
    """Root endpoint."""
    return jsonify({
        'service': SERVICE_NAME,
        'version': SERVICE_VERSION,
        'endpoints': ['/health', '/checkout', '/orders', '/orders/<order_id>']
    })


if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5003))
    print(f"\n🚀 Starting {SERVICE_NAME} on http://localhost:{port}")
    app.run(debug=False, host='0.0.0.0', port=port)

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

from ldobserve.observe import record_log, record_exception, start_span, LEVELS

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from shared.observability import create_ld_client, get_common_attributes, setup_flask_instrumentation
from shared.users import get_random_user
from shared.error_injection import maybe_raise_error, InjectedError
from shared.service_names import get_service_url

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

# Sample products
PRODUCTS = [
    {'id': 'prod_001', 'name': 'Feature Flag Starter Kit', 'price': 29.99},
    {'id': 'prod_002', 'name': 'Progressive Rollout Pro', 'price': 49.99},
    {'id': 'prod_003', 'name': 'A/B Testing Suite', 'price': 79.99},
    {'id': 'prod_004', 'name': 'Targeting Rules Package', 'price': 39.99},
    {'id': 'prod_005', 'name': 'Segment Builder', 'price': 59.99},
]


def get_trace_headers():
    """Extract trace context headers."""
    headers = {}
    for key in ['traceparent', 'tracestate']:
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
        
        maybe_raise_error(SERVICE_NAME, '/checkout')
        
        data = request.get_json() or {}
        user = data.get('user', get_random_user())
        items = data.get('items', random.sample(PRODUCTS, k=random.randint(1, 3)))
        
        order_id = f"ord_{uuid.uuid4().hex[:12]}"
        total = sum(item.get('price', 0) for item in items)
        
        span.set_attribute('order_id', order_id)
        span.set_attribute('item_count', len(items))
        span.set_attribute('total', total)
        
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
            except Exception as e:
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
            except Exception as e:
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
                record_log(f"Failed to send order confirmation: {e}", LEVELS['warning'], {
                    **get_common_attributes(SERVICE_NAME, '/checkout'),
                    'order_id': order_id,
                })
        
        record_log(f"Order {order_id} completed successfully", LEVELS['info'], {
            **get_common_attributes(SERVICE_NAME, '/checkout'),
            'order_id': order_id,
            'total': total,
            'status': 'completed',
        })
        
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
    """List recent orders."""
    with start_span('order.list') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)
        
        maybe_raise_error(SERVICE_NAME, '/orders')
        
        # Simulate database query
        time.sleep(0.2)
        
        # Generate some sample orders
        orders = []
        for i in range(5):
            user = get_random_user()
            items = random.sample(PRODUCTS, k=random.randint(1, 3))
            orders.append({
                'id': f"ord_{uuid.uuid4().hex[:12]}",
                'user': user,
                'items': items,
                'total': sum(item['price'] for item in items),
                'status': random.choice(['completed', 'processing', 'shipped']),
                'created_at': f"2024-12-0{i+1}T10:30:00Z",
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
    """Get order details."""
    with start_span('order.get') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)
        span.set_attribute('order_id', order_id)
        
        maybe_raise_error(SERVICE_NAME, '/orders')
        
        time.sleep(0.1)
        
        user = get_random_user()
        items = random.sample(PRODUCTS, k=random.randint(1, 3))
        
        return jsonify({
            'success': True,
            'service': SERVICE_NAME,
            'order': {
                'id': order_id,
                'user': user,
                'items': items,
                'total': sum(item['price'] for item in items),
                'status': 'completed',
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
    app.run(debug=True, host='0.0.0.0', port=port)

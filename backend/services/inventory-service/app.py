"""
Inventory Service - Stock management, reservations.
Port: 5005

This service simulates a warehouse API v2 migration gone wrong. Error
injection is isolated here to create a clear service map where one leaf
service is the obvious error source.

Architecture note: error injection is gated behind `should_use_unstable_api()`.
To integrate a LaunchDarkly feature flag, replace that function body with:

    return ld_client.variation("warehouse-api-migration", context, False)

The flag controls two variations:
  - "stable" (old warehouse API): no errors injected
  - "unstable" (new warehouse API v2): errors at configured rates
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

from ldobserve.observe import record_log, record_exception, start_span, LEVELS

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from shared.observability import create_ld_client, get_common_attributes, setup_flask_instrumentation
from shared.service_names import get_service_url

# Load environment variables
load_dotenv()

# Service configuration
SERVICE_NAME = os.getenv('SERVICE_NAME', 'inventory-service')
SERVICE_VERSION = os.getenv('SERVICE_VERSION', '1.0.0')
USE_DOCKER = os.getenv('USE_DOCKER', 'true').lower() == 'true'

# IMPORTANT: Initialize LaunchDarkly FIRST to set up tracer provider
client = create_ld_client(SERVICE_NAME, SERVICE_VERSION)

# Initialize Flask app
app = Flask(__name__)
CORS(app, expose_headers=['traceparent', 'tracestate'], allow_headers=['Content-Type', 'traceparent', 'tracestate'])

# Set up instrumentation AFTER LD client is initialized
setup_flask_instrumentation(app)


# ============================================================================
# WAREHOUSE API v2 ERROR INJECTION
#
# Simulates a warehouse API migration where the new v2 endpoints are
# unreliable. Errors are injected at realistic rates to produce compelling
# observability data (error traces, service map hotspots, error rate graphs).
# ============================================================================

class WarehouseAPIError(Exception):
    """Error from the warehouse API v2 migration."""

    def __init__(self, message: str, error_type: str, status_code: int = 500):
        super().__init__(message)
        self.error_type = error_type
        self.status_code = status_code


def should_use_unstable_api() -> bool:
    """
    Determine whether this request should use the "unstable" code path.

    Currently always returns True (all inventory requests use the new API).
    Replace this with a LaunchDarkly flag evaluation to control the rollout:

        return client.variation("warehouse-api-migration", context, False)
    """
    return True


# Error scenarios for the warehouse API v2 migration.
# Each scenario has a probability rate, the endpoints it affects,
# and the error details that appear in traces/logs.
WAREHOUSE_V2_ERRORS = [
    {
        "rate": 0.06,
        "endpoints": ["/reserve", "/check", "/products"],
        "error_type": "WarehouseAPIv2TimeoutError",
        "message": "Warehouse API v2: request timed out after 10s (endpoint: /v2/inventory/query)",
        "status_code": 504,
    },
    {
        "rate": 0.04,
        "endpoints": ["/reserve", "/check", "/products"],
        "error_type": "WarehouseAPIv2ResponseParseError",
        "message": "Warehouse API v2: unexpected response format — got 'available_qty' instead of 'quantity_on_hand'",
        "status_code": 500,
    },
    {
        "rate": 0.02,
        "endpoints": ["*"],
        "error_type": "WarehouseAPIv2AuthError",
        "message": "Warehouse API v2: authentication failed — API key rotation in progress",
        "status_code": 503,
    },
    {
        "rate": 0.03,
        "endpoints": ["/reserve", "/check"],
        "error_type": "WarehouseAPIv2RateLimitError",
        "message": "Warehouse API v2: rate limit exceeded (100 req/min) — retry after 12s",
        "status_code": 429,
    },
    {
        "rate": 0.03,
        "endpoints": ["/check", "/products"],
        "error_type": "StaleInventoryCacheError",
        "message": "Inventory cache invalidation failed — v2 cache key format mismatch",
        "status_code": 500,
    },
]


def maybe_get_warehouse_error(endpoint: str) -> Optional[WarehouseAPIError]:
    """
    Check if a warehouse API v2 error should be injected for this request.

    Returns a WarehouseAPIError if the dice roll triggers an error scenario,
    or None if the request should proceed normally. The caller raises the
    returned error so the stack trace points to the service's own route handler.
    """
    if not should_use_unstable_api():
        return None

    for scenario in WAREHOUSE_V2_ERRORS:
        # Check if this scenario applies to the current endpoint
        endpoints = scenario["endpoints"]
        if "*" not in endpoints and not any(
            endpoint.startswith(ep) for ep in endpoints
        ):
            continue

        # Roll the dice
        if random.random() < scenario["rate"]:
            return WarehouseAPIError(
                message=scenario["message"],
                error_type=scenario["error_type"],
                status_code=scenario["status_code"],
            )

    return None


# ============================================================================
# SAMPLE DATA
# ============================================================================

PRODUCTS = {
    'prod_001': {'id': 'prod_001', 'name': 'Feature Flag Starter Kit', 'price': 29.99, 'stock': 150, 'category': 'kits'},
    'prod_002': {'id': 'prod_002', 'name': 'Progressive Rollout Pro', 'price': 49.99, 'stock': 75, 'category': 'tools'},
    'prod_003': {'id': 'prod_003', 'name': 'A/B Testing Suite', 'price': 79.99, 'stock': 45, 'category': 'suites'},
    'prod_004': {'id': 'prod_004', 'name': 'Targeting Rules Package', 'price': 39.99, 'stock': 200, 'category': 'packages'},
    'prod_005': {'id': 'prod_005', 'name': 'Segment Builder', 'price': 59.99, 'stock': 100, 'category': 'tools'},
    'prod_006': {'id': 'prod_006', 'name': 'Experimentation Platform', 'price': 99.99, 'stock': 30, 'category': 'platforms'},
    'prod_007': {'id': 'prod_007', 'name': 'SDK Integration Kit', 'price': 19.99, 'stock': 500, 'category': 'kits'},
    'prod_008': {'id': 'prod_008', 'name': 'Release Automation', 'price': 149.99, 'stock': 25, 'category': 'platforms'},
}


# ============================================================================
# HELPERS
# ============================================================================

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
# INVENTORY ROUTES
# ============================================================================

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': SERVICE_NAME,
        'version': SERVICE_VERSION,
    })


@app.route('/products', methods=['GET'])
def list_products():
    """List all products."""
    with start_span('inventory.products.list') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)

        # Warehouse API v2 error injection
        _err = maybe_get_warehouse_error('/products')
        if _err:
            raise _err

        # Simulate database query
        time.sleep(0.15)

        products = list(PRODUCTS.values())

        record_log(f"Retrieved {len(products)} products", LEVELS['info'], {
            **get_common_attributes(SERVICE_NAME, '/products'),
            'product_count': len(products),
        })

        return jsonify({
            'success': True,
            'service': SERVICE_NAME,
            'products': products,
        })


@app.route('/products/<product_id>', methods=['GET'])
def get_product(product_id):
    """Get product details."""
    with start_span('inventory.products.get') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)
        span.set_attribute('product_id', product_id)

        # Warehouse API v2 error injection
        _err = maybe_get_warehouse_error('/products')
        if _err:
            raise _err

        time.sleep(0.1)

        product = PRODUCTS.get(product_id)

        if not product:
            record_log(f"Product {product_id} not found", LEVELS['warning'], {
                **get_common_attributes(SERVICE_NAME, f'/products/{product_id}'),
                'product_id': product_id,
            })
            return jsonify({
                'success': False,
                'error': 'ProductNotFound',
                'message': f'Product {product_id} not found',
            }), 404

        return jsonify({
            'success': True,
            'service': SERVICE_NAME,
            'product': product,
        })


@app.route('/check', methods=['POST'])
def check_stock():
    """Check stock availability for items."""
    with start_span('inventory.stock.check') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)

        # Warehouse API v2 error injection
        _err = maybe_get_warehouse_error('/check')
        if _err:
            raise _err

        data = request.get_json() or {}
        items = data.get('items', [])

        time.sleep(0.1)

        results = []
        for item in items:
            product_id = item.get('product_id')
            quantity = item.get('quantity', 1)
            product = PRODUCTS.get(product_id, {})
            stock = product.get('stock', 0)

            results.append({
                'product_id': product_id,
                'requested': quantity,
                'available': stock,
                'in_stock': stock >= quantity,
            })

        all_available = all(r['in_stock'] for r in results)

        record_log(f"Stock check: {'all available' if all_available else 'some unavailable'}",
                   LEVELS['info'] if all_available else LEVELS['warning'], {
            **get_common_attributes(SERVICE_NAME, '/check'),
            'items_checked': len(items),
            'all_available': all_available,
        })

        return jsonify({
            'success': True,
            'service': SERVICE_NAME,
            'all_available': all_available,
            'items': results,
        })


@app.route('/reserve', methods=['POST'])
def reserve_stock():
    """Reserve stock for an order."""
    with start_span('inventory.stock.reserve') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)

        # Warehouse API v2 error injection
        _err = maybe_get_warehouse_error('/reserve')
        if _err:
            raise _err

        data = request.get_json() or {}
        order_id = data.get('order_id', f"ord_{uuid.uuid4().hex[:12]}")
        items = data.get('items', [])

        reservation_id = f"res_{uuid.uuid4().hex[:12]}"

        span.set_attribute('order_id', order_id)
        span.set_attribute('reservation_id', reservation_id)
        span.set_attribute('item_count', len(items))

        # Simulate reservation process
        time.sleep(0.2)

        record_log(f"Stock reserved for order {order_id}", LEVELS['info'], {
            **get_common_attributes(SERVICE_NAME, '/reserve'),
            'order_id': order_id,
            'reservation_id': reservation_id,
            'items': len(items),
        })

        # Notify about low stock if applicable
        for item in items:
            product_id = item.get('product_id')
            product = PRODUCTS.get(product_id, {})
            if product.get('stock', 0) < 10:
                try:
                    call_service('notification-service', '/send', 'POST', {
                        'type': 'alert',
                        'template': 'low_stock_alert',
                        'product_id': product_id,
                        'current_stock': product.get('stock', 0),
                    })
                except Exception:
                    pass

        return jsonify({
            'success': True,
            'service': SERVICE_NAME,
            'reservation': {
                'id': reservation_id,
                'order_id': order_id,
                'items': items,
                'status': 'reserved',
                'expires_at': '2024-12-15T10:30:00Z',
            }
        })


@app.route('/release', methods=['POST'])
def release_reservation():
    """Release a stock reservation."""
    with start_span('inventory.stock.release') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)

        data = request.get_json() or {}
        reservation_id = data.get('reservation_id')

        time.sleep(0.1)

        record_log(f"Reservation {reservation_id} released", LEVELS['info'], {
            **get_common_attributes(SERVICE_NAME, '/release'),
            'reservation_id': reservation_id,
        })

        return jsonify({
            'success': True,
            'service': SERVICE_NAME,
            'message': f'Reservation {reservation_id} released',
        })


@app.route('/', methods=['GET'])
def root():
    """Root endpoint."""
    return jsonify({
        'service': SERVICE_NAME,
        'version': SERVICE_VERSION,
        'endpoints': ['/health', '/products', '/products/<id>', '/check', '/reserve', '/release']
    })


if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5005))
    print(f"\n🚀 Starting {SERVICE_NAME} on http://localhost:{port}")
    app.run(debug=False, host='0.0.0.0', port=port)

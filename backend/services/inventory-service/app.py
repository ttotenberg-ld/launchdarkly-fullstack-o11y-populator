"""
Inventory Service - Stock management, reservations.
Port: 5005

This service simulates a warehouse API migration. Error injection is
isolated here to create a clear service map where one leaf service is
the obvious error source.

Architecture note: error injection is gated behind `get_warehouse_api_version()`,
which evaluates the 'migrate-warehouse-api' LaunchDarkly feature flag.

The flag is multivariate (string) with three variations:
  - "v1" / Stable legacy:       original warehouse API, no errors
  - "v2" / Unstable migration:  new warehouse API v2, errors at configured rates
  - "v3" / Stable (iterated):   v2 after stabilization, errors resolved
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

from shared.observability import create_ld_client, build_service_context, get_common_attributes, setup_flask_instrumentation
from ldclient import Context
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


def _build_user_context() -> Optional[Context]:
    """
    Extract the frontend user from X-User-* headers and return a user
    context, or None when headers are absent (e.g. health checks).
    """
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
    """
    Build a multi-context for flag evaluations combining up to three kinds:
      - user    : the end-user from the frontend (via X-User-* headers)
      - request : an ephemeral anonymous context unique to each evaluation
      - service : the stable service identity
    """
    user_context = _build_user_context()

    if not user_context:
        record_log(
            "No X-User-* headers on request — user context omitted from multi-context",
            LEVELS['warning'],
            {
                **get_common_attributes(SERVICE_NAME, request.path),
                'method': request.method,
                'has_x_user_key': 'X-User-Key' in request.headers,
            },
        )

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


def get_warehouse_api_version() -> str:
    """
    Determine which warehouse API version to use for this request,
    controlled by the 'migrate-warehouse-api' LaunchDarkly feature flag.

    Returns "v1", "v2", or "v3":
      - "v1": stable legacy path (no error injection)
      - "v2": unstable migration (errors injected at configured rates)
      - "v3": stabilized v2 iteration (no error injection)
    """
    context = build_evaluation_context()

    flag_key = "migrate-warehouse-api"
    context_kinds = []
    for kind in ["user", "request", "service"]:
        if context.get_individual_context(kind) is not None:
            context_kinds.append(kind)

    record_log(
        f"Evaluating flag '{flag_key}'",
        LEVELS['debug'],
        {
            **get_common_attributes(SERVICE_NAME, request.path),
            'flag.key': flag_key,
            'ld.context.kinds': str(context_kinds),
            'ld.client.initialized': client.is_initialized(),
        },
    )

    detail = client.variation_detail(flag_key, context, "v1")
    flag_value = detail.value
    reason = detail.reason

    record_log(
        f"Flag '{flag_key}' evaluated to {flag_value}",
        LEVELS['info'],
        {
            **get_common_attributes(SERVICE_NAME, request.path),
            'flag.key': flag_key,
            'flag.value': flag_value,
            'flag.reason.kind': reason.get('kind') if reason else 'unknown',
            'flag.reason': str(reason),
            'flag.variation_index': detail.variation_index,
            'ld.client.initialized': client.is_initialized(),
        },
    )

    return flag_value


# Error scenarios for the warehouse API v2 migration.
# Each scenario has a probability rate, the endpoints it affects,
# the error details that appear in traces/logs, and a latency range
# (min_seconds, max_seconds) simulating the delay before the error
# surfaces (e.g. timeouts take a long time, rate limits are fast).
WAREHOUSE_V2_ERRORS = [
    {
        "rate": 0.06,
        "endpoints": ["/reserve", "/check", "/products"],
        "error_type": "WarehouseAPIv2TimeoutError",
        "message": "Warehouse API v2: request timed out after 10s (endpoint: /v2/inventory/query)",
        "status_code": 504,
        "latency": (3.0, 8.0),
    },
    {
        "rate": 0.04,
        "endpoints": ["/reserve", "/check", "/products"],
        "error_type": "WarehouseAPIv2ResponseParseError",
        "message": "Warehouse API v2: unexpected response format — got 'available_qty' instead of 'quantity_on_hand'",
        "status_code": 500,
        "latency": (0.5, 2.0),
    },
    {
        "rate": 0.02,
        "endpoints": ["*"],
        "error_type": "WarehouseAPIv2AuthError",
        "message": "Warehouse API v2: authentication failed — API key rotation in progress",
        "status_code": 503,
        "latency": (1.0, 3.0),
    },
    {
        "rate": 0.03,
        "endpoints": ["/reserve", "/check"],
        "error_type": "WarehouseAPIv2RateLimitError",
        "message": "Warehouse API v2: rate limit exceeded (100 req/min) — retry after 12s",
        "status_code": 429,
        "latency": (0.2, 0.8),
    },
    {
        "rate": 0.03,
        "endpoints": ["/check", "/products"],
        "error_type": "StaleInventoryCacheError",
        "message": "Inventory cache invalidation failed — v2 cache key format mismatch",
        "status_code": 500,
        "latency": (0.8, 2.5),
    },
]


def _scenario_matches_endpoint(scenario: dict, endpoint: str) -> bool:
    endpoints = scenario["endpoints"]
    if "*" in endpoints:
        return True
    return any(endpoint.startswith(ep) for ep in endpoints)


def maybe_get_warehouse_error(endpoint: str) -> Optional[WarehouseAPIError]:
    """
    Check if a warehouse API v2 error should be injected for this request.

    Returns a WarehouseAPIError if the dice roll triggers an error scenario,
    or None if the request should proceed normally. The caller raises the
    returned error so the stack trace points to the service's own route handler.
    """
    api_version = get_warehouse_api_version()
    record_log(
        f"Warehouse API path decision for {endpoint}: {api_version}",
        LEVELS['info'],
        {
            **get_common_attributes(SERVICE_NAME, endpoint),
            'flag.key': 'migrate-warehouse-api',
            'flag.value': api_version,
            'warehouse.api_version': api_version,
        },
    )

    # Only v2 injects errors — v1 (legacy) and v3 (stabilized) are stable
    if api_version != "v2":
        return None

    for scenario in WAREHOUSE_V2_ERRORS:
        if not _scenario_matches_endpoint(scenario, endpoint):
            continue

        # Roll the dice
        if random.random() < scenario["rate"]:
            # Simulate realistic latency before the error surfaces.
            # Timeouts take longer; rate limits are fast; parse errors
            # happen after some processing time.
            latency_range = scenario.get("latency", (0.1, 0.5))
            latency = random.uniform(*latency_range)
            record_log(
                f"Warehouse API v2 error pending: {scenario['error_type']} "
                f"(simulating {latency:.1f}s latency)",
                LEVELS['debug'],
                {
                    **get_common_attributes(SERVICE_NAME, endpoint),
                    'warehouse.error_type': scenario['error_type'],
                    'warehouse.simulated_latency_s': round(latency, 2),
                },
            )
            time.sleep(latency)

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

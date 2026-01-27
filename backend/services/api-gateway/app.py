"""
API Gateway Service - Routes requests and handles auth validation.
Port: 5000
"""

import os
import time
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

from ldobserve.observe import record_log, record_exception, start_span, LEVELS

# OpenTelemetry imports for diagnostics
from opentelemetry import trace
from opentelemetry.propagate import get_global_textmap

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from shared.observability import create_ld_client, get_common_attributes, setup_flask_instrumentation
from shared.users import get_random_user, get_user_context
from shared.error_injection import maybe_raise_error, InjectedError
from shared.service_names import get_service_url

# Load environment variables
load_dotenv()

# Service configuration
SERVICE_NAME = os.getenv('SERVICE_NAME', 'api-gateway')
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
# DIAGNOSTIC: Log trace context on every request
# ============================================================================
import sys
import logging

# Create a dedicated logger for trace debugging
trace_logger = logging.getLogger('trace_debug')
trace_logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter('%(message)s'))
trace_logger.addHandler(handler)

@app.before_request
def log_trace_context():
    """Log incoming trace context for debugging distributed tracing."""
    # Get incoming headers
    traceparent = request.headers.get('traceparent', 'NOT_PRESENT')
    tracestate = request.headers.get('tracestate', 'NOT_PRESENT')
    
    # Get the current span from OpenTelemetry
    current_span = trace.get_current_span()
    span_context = current_span.get_span_context() if current_span else None
    
    # Get the global propagator type
    propagator = get_global_textmap()
    propagator_type = type(propagator).__name__
    
    msg = [
        "",
        "=" * 60,
        f"[TRACE DEBUG] {request.method} {request.path}",
        f"  Incoming traceparent: {traceparent}",
        f"  Incoming tracestate: {tracestate}",
        f"  Global propagator: {propagator_type}",
    ]
    
    if span_context:
        msg.extend([
            f"  Current span trace_id: {format(span_context.trace_id, '032x')}",
            f"  Current span span_id: {format(span_context.span_id, '016x')}",
            f"  Current span is_valid: {span_context.is_valid}",
            f"  Current span is_remote: {span_context.is_remote}",
        ])
    else:
        msg.append("  Current span: None")
    
    msg.append("=" * 60)
    
    for line in msg:
        trace_logger.info(line)
    sys.stdout.flush()


def get_trace_headers():
    """Extract trace context headers from the incoming request."""
    headers = {}
    for key in ['traceparent', 'tracestate']:
        if key in request.headers:
            headers[key] = request.headers[key]
    return headers


def call_service(service_name: str, path: str, method: str = 'GET', data: dict = None) -> dict:
    """Call a downstream service with trace context propagation."""
    url = get_service_url(service_name, USE_DOCKER) + path
    headers = get_trace_headers()
    headers['Content-Type'] = 'application/json'
    
    try:
        if method == 'GET':
            resp = requests.get(url, headers=headers, timeout=30)
        elif method == 'POST':
            resp = requests.post(url, json=data, headers=headers, timeout=30)
        elif method == 'PUT':
            resp = requests.put(url, json=data, headers=headers, timeout=30)
        elif method == 'DELETE':
            resp = requests.delete(url, headers=headers, timeout=30)
        else:
            resp = requests.request(method, url, json=data, headers=headers, timeout=30)
        
        return resp.json()
    except requests.exceptions.RequestException as e:
        record_exception(e, {
            **get_common_attributes(SERVICE_NAME, path),
            'downstream_service': service_name,
            'error_type': 'downstream_call_failed',
        })
        raise


# Global error handler
@app.errorhandler(Exception)
def handle_exception(error):
    """Global error handler that records all exceptions."""
    status_code = getattr(error, 'status_code', 500)
    error_type = getattr(error, 'error_type', type(error).__name__)
    
    record_exception(error, {
        **get_common_attributes(SERVICE_NAME, request.path),
        'error_type': error_type,
        'method': request.method,
    })
    
    return jsonify({
        'success': False,
        'error': error_type,
        'message': str(error),
        'service': SERVICE_NAME,
    }), status_code


# ============================================================================
# GATEWAY ROUTES
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': SERVICE_NAME,
        'version': SERVICE_VERSION,
    })


@app.route('/api/login', methods=['POST'])
def login():
    """Login endpoint - forwards to auth-service."""
    with start_span('gateway.auth.login') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)
        
        maybe_raise_error(SERVICE_NAME, '/api/login')
        
        user = get_random_user()
        data = request.get_json() or {}
        data['user'] = user
        
        record_log(f"Login request for {user['email']}", LEVELS['info'], {
            **get_common_attributes(SERVICE_NAME, '/api/login'),
            'user_email': user['email'],
        })
        
        result = call_service('auth-service', '/login', 'POST', data)
        return jsonify(result)


@app.route('/api/users/<user_id>', methods=['GET'])
def get_user(user_id):
    """Get user profile - forwards to user-service."""
    with start_span('gateway.users.get') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)
        span.set_attribute('user_id', user_id)
        
        maybe_raise_error(SERVICE_NAME, '/api/users')
        
        record_log(f"Fetching user profile for {user_id}", LEVELS['info'], {
            **get_common_attributes(SERVICE_NAME, f'/api/users/{user_id}'),
            'user_id': user_id,
        })
        
        result = call_service('user-service', f'/users/{user_id}')
        return jsonify(result)


@app.route('/api/users/<user_id>', methods=['PUT'])
def update_user(user_id):
    """Update user profile - forwards to user-service."""
    with start_span('gateway.users.update') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)
        span.set_attribute('user_id', user_id)
        
        maybe_raise_error(SERVICE_NAME, '/api/users')
        
        data = request.get_json() or {}
        
        record_log(f"Updating user profile for {user_id}", LEVELS['info'], {
            **get_common_attributes(SERVICE_NAME, f'/api/users/{user_id}'),
            'user_id': user_id,
        })
        
        result = call_service('user-service', f'/users/{user_id}', 'PUT', data)
        return jsonify(result)


@app.route('/api/checkout', methods=['POST'])
def checkout():
    """Checkout endpoint - forwards to order-service."""
    with start_span('gateway.orders.checkout') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)
        
        maybe_raise_error(SERVICE_NAME, '/api/checkout')
        
        user = get_random_user()
        data = request.get_json() or {}
        data['user'] = user
        
        record_log(f"Checkout initiated by {user['email']}", LEVELS['info'], {
            **get_common_attributes(SERVICE_NAME, '/api/checkout'),
            'user_email': user['email'],
            'cart_items': len(data.get('items', [])),
        })
        
        result = call_service('order-service', '/checkout', 'POST', data)
        return jsonify(result)


@app.route('/api/orders', methods=['GET'])
def list_orders():
    """List orders - forwards to order-service."""
    with start_span('gateway.orders.list') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)
        
        maybe_raise_error(SERVICE_NAME, '/api/orders')
        
        result = call_service('order-service', '/orders')
        return jsonify(result)


@app.route('/api/search', methods=['POST'])
def search():
    """Search endpoint - forwards to search-service."""
    with start_span('gateway.search.query') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)
        
        maybe_raise_error(SERVICE_NAME, '/api/search')
        
        data = request.get_json() or {}
        query = data.get('query', '')
        
        record_log(f"Search query: {query}", LEVELS['info'], {
            **get_common_attributes(SERVICE_NAME, '/api/search'),
            'query': query,
        })
        
        result = call_service('search-service', '/search', 'POST', data)
        return jsonify(result)


@app.route('/api/products', methods=['GET'])
def list_products():
    """List products - forwards to inventory-service."""
    with start_span('gateway.products.list') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)
        
        maybe_raise_error(SERVICE_NAME, '/api/products')
        
        result = call_service('inventory-service', '/products')
        return jsonify(result)


@app.route('/api/products/<product_id>', methods=['GET'])
def get_product(product_id):
    """Get product - forwards to inventory-service."""
    with start_span('gateway.products.get') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)
        span.set_attribute('product_id', product_id)
        
        maybe_raise_error(SERVICE_NAME, '/api/products')
        
        result = call_service('inventory-service', f'/products/{product_id}')
        return jsonify(result)


@app.route('/api/dashboard', methods=['GET'])
def dashboard():
    """Dashboard data - aggregates from multiple services."""
    with start_span('gateway.dashboard.aggregate') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)
        
        maybe_raise_error(SERVICE_NAME, '/api/dashboard')
        
        record_log("Dashboard data requested", LEVELS['info'], 
                   get_common_attributes(SERVICE_NAME, '/api/dashboard'))
        
        # Simulate aggregating data from multiple services
        time.sleep(0.1)
        
        return jsonify({
            'success': True,
            'service': SERVICE_NAME,
            'data': {
                'active_users': 1247,
                'orders_today': 89,
                'revenue_today': 12450.00,
                'pending_orders': 12,
                'inventory_alerts': 3,
            }
        })


@app.route('/', methods=['GET'])
def root():
    """Root endpoint."""
    return jsonify({
        'message': 'LaunchDarkly Observability Demo - API Gateway',
        'service': SERVICE_NAME,
        'version': SERVICE_VERSION,
        'endpoints': [
            '/api/health',
            '/api/login',
            '/api/users/<user_id>',
            '/api/checkout',
            '/api/orders',
            '/api/search',
            '/api/products',
            '/api/dashboard',
        ]
    })


if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5000))
    print(f"\n🚀 Starting {SERVICE_NAME} on http://localhost:{port}")
    app.run(debug=True, host='0.0.0.0', port=port)

"""
Auth Service - Login, token validation, sessions.
Port: 5001
"""

import os
import time
import uuid
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

from ldobserve.observe import record_log, record_exception, start_span, LEVELS

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from shared.observability import create_ld_client, get_common_attributes, setup_flask_instrumentation
from shared.users import get_random_user, get_user_by_key
from shared.error_injection import maybe_raise_error, InjectedError
from shared.service_names import get_service_url

# Load environment variables
load_dotenv()

# Service configuration
SERVICE_NAME = os.getenv('SERVICE_NAME', 'auth-service')
SERVICE_VERSION = os.getenv('SERVICE_VERSION', '1.0.0')
USE_DOCKER = os.getenv('USE_DOCKER', 'true').lower() == 'true'

# IMPORTANT: Initialize LaunchDarkly FIRST to set up tracer provider
client = create_ld_client(SERVICE_NAME, SERVICE_VERSION)

# Initialize Flask app
app = Flask(__name__)
CORS(app, expose_headers=['traceparent', 'tracestate'], allow_headers=['Content-Type', 'traceparent', 'tracestate'])

# Set up instrumentation AFTER LD client is initialized
setup_flask_instrumentation(app)


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
# AUTH ROUTES
# ============================================================================

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': SERVICE_NAME,
        'version': SERVICE_VERSION,
    })


@app.route('/login', methods=['POST'])
def login():
    """Authenticate user and generate token."""
    with start_span('auth.login') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)
        
        maybe_raise_error(SERVICE_NAME, '/login')
        
        data = request.get_json() or {}
        user = data.get('user', get_random_user())
        
        # Simulate authentication delay
        time.sleep(0.2)
        
        # Generate session token
        token = str(uuid.uuid4())
        
        record_log(f"User {user['email']} authenticated successfully", LEVELS['info'], {
            **get_common_attributes(SERVICE_NAME, '/login'),
            'user_key': user['key'],
            'user_email': user['email'],
            'auth_method': 'password',
        })
        
        # Track login event in analytics
        try:
            call_service('analytics-service', '/track', 'POST', {
                'event': 'user.login',
                'user': user,
                'properties': {
                    'auth_method': 'password',
                    'timestamp': time.time(),
                }
            })
        except Exception as e:
            record_log(f"Failed to track login event: {e}", LEVELS['warning'], 
                       get_common_attributes(SERVICE_NAME, '/login'))
        
        span.set_attribute('login.success', True)
        
        return jsonify({
            'success': True,
            'service': SERVICE_NAME,
            'user': user,
            'token': token,
            'expires_in': 3600,
        })


@app.route('/validate', methods=['POST'])
def validate_token():
    """Validate an authentication token."""
    with start_span('auth.validate') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)
        
        maybe_raise_error(SERVICE_NAME, '/validate')
        
        data = request.get_json() or {}
        token = data.get('token', '')
        
        # Simulate token validation
        time.sleep(0.05)
        
        is_valid = len(token) > 10  # Simple validation
        
        record_log(f"Token validation: {'valid' if is_valid else 'invalid'}", 
                   LEVELS['info'] if is_valid else LEVELS['warning'], {
            **get_common_attributes(SERVICE_NAME, '/validate'),
            'token_valid': is_valid,
        })
        
        span.set_attribute('token.valid', is_valid)
        
        return jsonify({
            'success': True,
            'service': SERVICE_NAME,
            'valid': is_valid,
            'user_key': 'usr_001' if is_valid else None,
        })


@app.route('/refresh', methods=['POST'])
def refresh_token():
    """Refresh an authentication token."""
    with start_span('auth.refresh') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)
        
        maybe_raise_error(SERVICE_NAME, '/refresh')
        
        data = request.get_json() or {}
        old_token = data.get('token', '')
        
        # Simulate token refresh
        time.sleep(0.1)
        
        new_token = str(uuid.uuid4())
        
        record_log("Token refreshed successfully", LEVELS['info'], {
            **get_common_attributes(SERVICE_NAME, '/refresh'),
        })
        
        return jsonify({
            'success': True,
            'service': SERVICE_NAME,
            'token': new_token,
            'expires_in': 3600,
        })


@app.route('/logout', methods=['POST'])
def logout():
    """Invalidate user session."""
    with start_span('auth.logout') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)
        
        data = request.get_json() or {}
        user_key = data.get('user_key', 'unknown')
        
        record_log(f"User {user_key} logged out", LEVELS['info'], {
            **get_common_attributes(SERVICE_NAME, '/logout'),
            'user_key': user_key,
        })
        
        # Track logout event
        try:
            call_service('analytics-service', '/track', 'POST', {
                'event': 'user.logout',
                'user_key': user_key,
            })
        except Exception:
            pass
        
        return jsonify({
            'success': True,
            'service': SERVICE_NAME,
            'message': 'Logged out successfully',
        })


@app.route('/', methods=['GET'])
def root():
    """Root endpoint."""
    return jsonify({
        'service': SERVICE_NAME,
        'version': SERVICE_VERSION,
        'endpoints': ['/health', '/login', '/validate', '/refresh', '/logout']
    })


if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5001))
    print(f"\n🚀 Starting {SERVICE_NAME} on http://localhost:{port}")
    app.run(debug=True, host='0.0.0.0', port=port)

"""
User Service - User profiles, preferences, settings.
Port: 5002
"""

import os
import time
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from dotenv import load_dotenv

from ldobserve.observe import record_log, record_exception, start_span, LEVELS

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from shared.observability import create_ld_client, get_common_attributes
from shared.users import get_user_by_key, USER_PERSONAS
from shared.error_injection import maybe_raise_error, InjectedError
from shared.service_names import get_service_url

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app, expose_headers=['traceparent', 'tracestate'], allow_headers=['Content-Type', 'traceparent', 'tracestate'])
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()

# Service configuration
SERVICE_NAME = os.getenv('SERVICE_NAME', 'user-service')
SERVICE_VERSION = os.getenv('SERVICE_VERSION', '1.0.0')
USE_DOCKER = os.getenv('USE_DOCKER', 'true').lower() == 'true'

# Initialize LaunchDarkly
client = create_ld_client(SERVICE_NAME, SERVICE_VERSION)


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
# USER ROUTES
# ============================================================================

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': SERVICE_NAME,
        'version': SERVICE_VERSION,
    })


@app.route('/users/<user_id>', methods=['GET'])
def get_user(user_id):
    """Get user profile by ID."""
    with start_span('user.profile.get') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)
        span.set_attribute('user_id', user_id)
        
        maybe_raise_error(SERVICE_NAME, '/users')
        
        # Simulate database lookup
        time.sleep(0.15)
        
        user = get_user_by_key(user_id)
        
        record_log(f"Retrieved profile for user {user['email']}", LEVELS['info'], {
            **get_common_attributes(SERVICE_NAME, f'/users/{user_id}'),
            'user_key': user['key'],
        })
        
        # Track profile view
        try:
            call_service('analytics-service', '/track', 'POST', {
                'event': 'user.profile.viewed',
                'user_key': user_id,
            })
        except Exception:
            pass
        
        return jsonify({
            'success': True,
            'service': SERVICE_NAME,
            'user': {
                **user,
                'created_at': '2024-01-15T10:30:00Z',
                'last_login': '2024-12-01T14:22:00Z',
                'preferences': {
                    'theme': 'dark',
                    'notifications': True,
                    'language': 'en',
                }
            }
        })


@app.route('/users/<user_id>', methods=['PUT'])
def update_user(user_id):
    """Update user profile."""
    with start_span('user.profile.update') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)
        span.set_attribute('user_id', user_id)
        
        maybe_raise_error(SERVICE_NAME, '/users')
        
        data = request.get_json() or {}
        
        # Simulate database update
        time.sleep(0.2)
        
        record_log(f"Updated profile for user {user_id}", LEVELS['info'], {
            **get_common_attributes(SERVICE_NAME, f'/users/{user_id}'),
            'user_key': user_id,
            'updated_fields': list(data.keys()),
        })
        
        # Track profile update
        try:
            call_service('analytics-service', '/track', 'POST', {
                'event': 'user.profile.updated',
                'user_key': user_id,
                'properties': {'fields': list(data.keys())},
            })
        except Exception:
            pass
        
        # Send notification
        try:
            call_service('notification-service', '/send', 'POST', {
                'type': 'email',
                'template': 'profile_updated',
                'user_key': user_id,
            })
        except Exception:
            pass
        
        return jsonify({
            'success': True,
            'service': SERVICE_NAME,
            'message': 'Profile updated successfully',
            'user_key': user_id,
        })


@app.route('/users/<user_id>/preferences', methods=['GET'])
def get_preferences(user_id):
    """Get user preferences."""
    with start_span('user.preferences.get') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)
        
        maybe_raise_error(SERVICE_NAME, '/users')
        
        time.sleep(0.1)
        
        return jsonify({
            'success': True,
            'service': SERVICE_NAME,
            'preferences': {
                'theme': 'dark',
                'notifications': {
                    'email': True,
                    'push': True,
                    'sms': False,
                },
                'language': 'en',
                'timezone': 'America/New_York',
            }
        })


@app.route('/users/<user_id>/preferences', methods=['PUT'])
def update_preferences(user_id):
    """Update user preferences."""
    with start_span('user.preferences.update') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)
        
        maybe_raise_error(SERVICE_NAME, '/users')
        
        data = request.get_json() or {}
        time.sleep(0.15)
        
        record_log(f"Updated preferences for user {user_id}", LEVELS['info'], {
            **get_common_attributes(SERVICE_NAME, f'/users/{user_id}/preferences'),
            'user_key': user_id,
        })
        
        return jsonify({
            'success': True,
            'service': SERVICE_NAME,
            'message': 'Preferences updated',
        })


@app.route('/profile', methods=['GET'])
def get_current_profile():
    """Get current user's profile (from session)."""
    with start_span('user.profile.current') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)
        
        maybe_raise_error(SERVICE_NAME, '/profile')
        
        # Get a random user to simulate current session
        import random
        user = random.choice(USER_PERSONAS)
        
        time.sleep(0.1)
        
        return jsonify({
            'success': True,
            'service': SERVICE_NAME,
            'user': user,
        })


@app.route('/', methods=['GET'])
def root():
    """Root endpoint."""
    return jsonify({
        'service': SERVICE_NAME,
        'version': SERVICE_VERSION,
        'endpoints': ['/health', '/users/<user_id>', '/users/<user_id>/preferences', '/profile']
    })


if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5002))
    print(f"\n🚀 Starting {SERVICE_NAME} on http://localhost:{port}")
    app.run(debug=True, host='0.0.0.0', port=port)

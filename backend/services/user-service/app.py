"""
User Service - User profiles, preferences, settings.
Port: 5002
"""

import os
import time
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

from ldobserve.observe import record_log, record_exception, start_span, LEVELS

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from shared.observability import create_ld_client, get_common_attributes, setup_flask_instrumentation
from shared.users import get_user_by_key, USER_PERSONAS
from shared.db import get_engine, install_trace_attributes

from shared.service_names import get_service_url
from sqlalchemy import text

# Load environment variables
load_dotenv()

# Service configuration
SERVICE_NAME = os.getenv('SERVICE_NAME', 'user-service')
SERVICE_VERSION = os.getenv('SERVICE_VERSION', '1.0.0')
USE_DOCKER = os.getenv('USE_DOCKER', 'true').lower() == 'true'

# IMPORTANT: Initialize LaunchDarkly FIRST to set up tracer provider
client = create_ld_client(SERVICE_NAME, SERVICE_VERSION)

# Initialize Flask app
app = Flask(__name__)
CORS(app, expose_headers=['traceparent', 'tracestate'], allow_headers=['Content-Type', 'traceparent', 'tracestate'])

# Set up instrumentation AFTER LD client is initialized
setup_flask_instrumentation(app)

# Database engine for userdb — auto-instrumented for OTel tracing
engine = get_engine(default_db='userdb')
install_trace_attributes(engine, SERVICE_NAME)


USER_HEADERS = ['X-User-Key', 'X-User-Name', 'X-User-Email', 'X-User-Plan', 'X-User-Role', 'X-User-Metro', 'X-User-Country']


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


def _header_user() -> dict:
    """Pull the user context the gateway/simulator forwarded via X-User-* headers."""
    return {
        'key':     request.headers.get('X-User-Key'),
        'name':    request.headers.get('X-User-Name'),
        'email':   request.headers.get('X-User-Email'),
        'plan':    request.headers.get('X-User-Plan'),
        'role':    request.headers.get('X-User-Role'),
        'metro':   request.headers.get('X-User-Metro'),
        'country': request.headers.get('X-User-Country'),
    }


def db_upsert_user(u: dict) -> None:
    """Upsert a user row; touches last_login every time they're seen."""
    if not u.get('key'):
        return
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO users (key, name, email, plan, role, metro, country, last_login)
                VALUES (:key, :name, :email, :plan, :role, :metro, :country, NOW())
                ON CONFLICT (key) DO UPDATE SET
                    name       = COALESCE(EXCLUDED.name, users.name),
                    email      = COALESCE(EXCLUDED.email, users.email),
                    plan       = COALESCE(EXCLUDED.plan, users.plan),
                    role       = COALESCE(EXCLUDED.role, users.role),
                    metro      = COALESCE(EXCLUDED.metro, users.metro),
                    country    = COALESCE(EXCLUDED.country, users.country),
                    last_login = NOW()
            """),
            u,
        )
        # Ensure a preferences row exists so GETs work.
        conn.execute(
            text("""
                INSERT INTO user_preferences (user_key) VALUES (:key)
                ON CONFLICT (user_key) DO NOTHING
            """),
            {'key': u['key']},
        )


def db_get_user(user_key: str) -> dict | None:
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT key, name, email, plan, role, metro, country, created_at, last_login
                FROM users
                WHERE key = :key
            """),
            {'key': user_key},
        ).first()
    if not row:
        return None
    return {
        'key':     row.key,
        'name':    row.name,
        'email':   row.email,
        'plan':    row.plan,
        'role':    row.role,
        'metro':   row.metro,
        'country': row.country,
        'created_at': row.created_at.isoformat() + 'Z' if row.created_at else None,
        'last_login': row.last_login.isoformat() + 'Z' if row.last_login else None,
    }


def db_get_preferences(user_key: str) -> dict | None:
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT theme, email_notify, push_notify, sms_notify, language, timezone
                FROM user_preferences
                WHERE user_key = :key
            """),
            {'key': user_key},
        ).first()
    if not row:
        return None
    return {
        'theme': row.theme,
        'notifications': {
            'email': bool(row.email_notify),
            'push':  bool(row.push_notify),
            'sms':   bool(row.sms_notify),
        },
        'language': row.language,
        'timezone': row.timezone,
    }


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

        # If the caller forwarded an X-User-* context for this id, upsert so
        # the table stays in sync with live simulator traffic.
        header_user = _header_user()
        if header_user.get('key') == user_id:
            db_upsert_user(header_user)

        user = db_get_user(user_id)

        if user is None:
            # Backfill from the static persona helper if we've never seen this
            # key before (keeps the endpoint from 404'ing on random sim users).
            fallback = get_user_by_key(user_id)
            db_upsert_user(fallback)
            user = db_get_user(user_id) or fallback

        prefs = db_get_preferences(user_id) or {
            'theme': 'dark',
            'notifications': {'email': True, 'push': True, 'sms': False},
            'language': 'en',
            'timezone': 'America/New_York',
        }

        record_log(f"Retrieved profile for user {user.get('email')}", LEVELS['info'], {
            **get_common_attributes(SERVICE_NAME, f'/users/{user_id}'),
            'user_key': user.get('key'),
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
                'preferences': prefs,
            }
        })


@app.route('/users/<user_id>', methods=['PUT'])
def update_user(user_id):
    """Update user profile."""
    with start_span('user.profile.update') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)
        span.set_attribute('user_id', user_id)

        data = request.get_json() or {}

        # Only update columns the client actually passed. COALESCE lets us
        # short-circuit nulls so partial updates don't wipe other fields.
        allowed = {'name', 'email', 'plan', 'role', 'metro', 'country'}
        updates = {k: v for k, v in data.items() if k in allowed}
        span.set_attribute('updated_fields', ','.join(sorted(updates.keys())))

        with engine.begin() as conn:
            # Ensure the row exists first so the UPDATE has something to hit.
            conn.execute(
                text("INSERT INTO users (key) VALUES (:key) ON CONFLICT (key) DO NOTHING"),
                {'key': user_id},
            )
            if updates:
                set_clause = ', '.join(f"{col} = :{col}" for col in updates)
                conn.execute(
                    text(f"UPDATE users SET {set_clause} WHERE key = :key"),
                    {**updates, 'key': user_id},
                )

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
        span.set_attribute('user_id', user_id)

        prefs = db_get_preferences(user_id)
        if prefs is None:
            # Lazily create the user + preferences row.
            db_upsert_user({'key': user_id, **_header_user()})
            prefs = db_get_preferences(user_id) or {
                'theme': 'dark',
                'notifications': {'email': True, 'push': True, 'sms': False},
                'language': 'en',
                'timezone': 'America/New_York',
            }

        return jsonify({
            'success': True,
            'service': SERVICE_NAME,
            'preferences': prefs,
        })


@app.route('/users/<user_id>/preferences', methods=['PUT'])
def update_preferences(user_id):
    """Update user preferences."""
    with start_span('user.preferences.update') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)
        span.set_attribute('user_id', user_id)

        data = request.get_json() or {}

        # Flatten the nested notifications object the frontend sends.
        notifications = data.get('notifications') or {}
        flat = {
            'theme':        data.get('theme'),
            'email_notify': notifications.get('email'),
            'push_notify':  notifications.get('push'),
            'sms_notify':   notifications.get('sms'),
            'language':     data.get('language'),
            'timezone':     data.get('timezone'),
        }
        updates = {k: v for k, v in flat.items() if v is not None}
        span.set_attribute('updated_fields', ','.join(sorted(updates.keys())))

        with engine.begin() as conn:
            # Make sure the row exists — FK to users(key) requires the user row.
            conn.execute(
                text("INSERT INTO users (key) VALUES (:key) ON CONFLICT (key) DO NOTHING"),
                {'key': user_id},
            )
            conn.execute(
                text("""
                    INSERT INTO user_preferences (user_key) VALUES (:key)
                    ON CONFLICT (user_key) DO NOTHING
                """),
                {'key': user_id},
            )
            if updates:
                set_clause = ', '.join(f"{col} = :{col}" for col in updates)
                conn.execute(
                    text(f"UPDATE user_preferences SET {set_clause}, updated_at = NOW() WHERE user_key = :key"),
                    {**updates, 'key': user_id},
                )

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
    app.run(debug=False, host='0.0.0.0', port=port)

"""
Analytics Service - Event tracking and metrics.
Port: 5007
"""

import os
import time
import uuid
import random
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

from ldobserve.observe import record_log, record_exception, start_span, LEVELS

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from shared.observability import create_ld_client, get_common_attributes, setup_flask_instrumentation
from shared.error_injection import maybe_raise_error, InjectedError

# Load environment variables
load_dotenv()

# Service configuration
SERVICE_NAME = os.getenv('SERVICE_NAME', 'analytics-service')
SERVICE_VERSION = os.getenv('SERVICE_VERSION', '1.0.0')

# IMPORTANT: Initialize LaunchDarkly FIRST to set up tracer provider
client = create_ld_client(SERVICE_NAME, SERVICE_VERSION)

# Initialize Flask app
app = Flask(__name__)
CORS(app, expose_headers=['traceparent', 'tracestate'], allow_headers=['Content-Type', 'traceparent', 'tracestate'])

# Set up instrumentation AFTER LD client is initialized
setup_flask_instrumentation(app)


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
# ANALYTICS ROUTES
# ============================================================================

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': SERVICE_NAME,
        'version': SERVICE_VERSION,
    })


@app.route('/track', methods=['POST'])
def track_event():
    """Track an analytics event."""
    with start_span('analytics.track') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)
        
        maybe_raise_error(SERVICE_NAME, '/track')
        
        data = request.get_json() or {}
        event_name = data.get('event', 'unknown_event')
        user = data.get('user', {})
        user_key = data.get('user_key') or user.get('key', 'anonymous')
        properties = data.get('properties', {})
        
        event_id = f"evt_{uuid.uuid4().hex[:12]}"
        
        span.set_attribute('event_id', event_id)
        span.set_attribute('event_name', event_name)
        span.set_attribute('user_key', user_key)
        
        # Simulate event processing
        time.sleep(0.05)
        
        record_log(f"Event tracked: {event_name}", LEVELS['debug'], {
            **get_common_attributes(SERVICE_NAME, '/track'),
            'event_id': event_id,
            'event_name': event_name,
            'user_key': user_key,
            'properties': str(properties),
        })
        
        return jsonify({
            'success': True,
            'service': SERVICE_NAME,
            'event': {
                'id': event_id,
                'name': event_name,
                'user_key': user_key,
                'timestamp': time.time(),
            }
        })


@app.route('/events', methods=['POST'])
def track_batch():
    """Track multiple events in a batch."""
    with start_span('analytics.track_batch') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)
        
        maybe_raise_error(SERVICE_NAME, '/events')
        
        data = request.get_json() or {}
        events = data.get('events', [])
        
        span.set_attribute('batch_size', len(events))
        
        # Simulate batch processing
        time.sleep(0.02 * len(events))
        
        record_log(f"Batch tracked: {len(events)} events", LEVELS['info'], {
            **get_common_attributes(SERVICE_NAME, '/events'),
            'batch_size': len(events),
        })
        
        return jsonify({
            'success': True,
            'service': SERVICE_NAME,
            'processed': len(events),
        })


@app.route('/pageview', methods=['POST'])
def track_pageview():
    """Track a page view."""
    with start_span('analytics.pageview') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)
        
        data = request.get_json() or {}
        page = data.get('page', '/')
        user_key = data.get('user_key', 'anonymous')
        referrer = data.get('referrer', '')
        
        time.sleep(0.03)
        
        record_log(f"Pageview: {page}", LEVELS['debug'], {
            **get_common_attributes(SERVICE_NAME, '/pageview'),
            'page': page,
            'user_key': user_key,
            'referrer': referrer,
        })
        
        return jsonify({
            'success': True,
            'service': SERVICE_NAME,
            'pageview': {
                'page': page,
                'user_key': user_key,
                'timestamp': time.time(),
            }
        })


@app.route('/metrics', methods=['GET'])
def get_metrics():
    """Get aggregated metrics."""
    with start_span('analytics.metrics') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)
        
        # Simulate metrics aggregation
        time.sleep(0.2)
        
        # Generate realistic metrics
        metrics = {
            'daily_active_users': random.randint(1000, 5000),
            'sessions_today': random.randint(2000, 8000),
            'avg_session_duration': random.randint(120, 600),
            'conversion_rate': round(random.uniform(0.02, 0.08), 4),
            'bounce_rate': round(random.uniform(0.3, 0.5), 4),
            'page_views_today': random.randint(10000, 50000),
            'events_tracked_today': random.randint(50000, 200000),
            'top_events': [
                {'name': 'user.login', 'count': random.randint(500, 2000)},
                {'name': 'product.viewed', 'count': random.randint(1000, 5000)},
                {'name': 'cart.add', 'count': random.randint(200, 800)},
                {'name': 'checkout.complete', 'count': random.randint(50, 200)},
            ],
        }
        
        record_log("Metrics retrieved", LEVELS['info'], 
                   get_common_attributes(SERVICE_NAME, '/metrics'))
        
        return jsonify({
            'success': True,
            'service': SERVICE_NAME,
            'metrics': metrics,
            'period': 'today',
        })


@app.route('/funnel', methods=['GET'])
def get_funnel():
    """Get funnel analysis."""
    with start_span('analytics.funnel') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)
        
        time.sleep(0.15)
        
        # Simulate funnel data
        funnel = {
            'name': 'Purchase Funnel',
            'steps': [
                {'name': 'Product View', 'count': 10000, 'rate': 1.0},
                {'name': 'Add to Cart', 'count': 3500, 'rate': 0.35},
                {'name': 'Begin Checkout', 'count': 1200, 'rate': 0.12},
                {'name': 'Complete Purchase', 'count': 450, 'rate': 0.045},
            ],
            'overall_conversion': 0.045,
        }
        
        return jsonify({
            'success': True,
            'service': SERVICE_NAME,
            'funnel': funnel,
        })


@app.route('/', methods=['GET'])
def root():
    """Root endpoint."""
    return jsonify({
        'service': SERVICE_NAME,
        'version': SERVICE_VERSION,
        'endpoints': ['/health', '/track', '/events', '/pageview', '/metrics', '/funnel']
    })


if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5007))
    print(f"\n🚀 Starting {SERVICE_NAME} on http://localhost:{port}")
    app.run(debug=True, host='0.0.0.0', port=port)

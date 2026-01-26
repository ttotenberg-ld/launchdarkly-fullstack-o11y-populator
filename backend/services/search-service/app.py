"""
Search Service - Product and user search.
Port: 5008
"""

import os
import time
import random
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
from shared.error_injection import maybe_raise_error, InjectedError
from shared.service_names import get_service_url

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()

# Service configuration
SERVICE_NAME = os.getenv('SERVICE_NAME', 'search-service')
SERVICE_VERSION = os.getenv('SERVICE_VERSION', '1.0.0')
USE_DOCKER = os.getenv('USE_DOCKER', 'true').lower() == 'true'

# Initialize LaunchDarkly
client = create_ld_client(SERVICE_NAME, SERVICE_VERSION)

# Sample search data
SEARCH_DATA = [
    {'id': 'prod_001', 'name': 'Feature Flag Starter Kit', 'category': 'kits', 'tags': ['starter', 'beginner', 'flags']},
    {'id': 'prod_002', 'name': 'Progressive Rollout Pro', 'category': 'tools', 'tags': ['rollout', 'progressive', 'release']},
    {'id': 'prod_003', 'name': 'A/B Testing Suite', 'category': 'suites', 'tags': ['testing', 'ab', 'experiment']},
    {'id': 'prod_004', 'name': 'Targeting Rules Package', 'category': 'packages', 'tags': ['targeting', 'rules', 'segments']},
    {'id': 'prod_005', 'name': 'Segment Builder', 'category': 'tools', 'tags': ['segments', 'builder', 'targeting']},
    {'id': 'prod_006', 'name': 'Experimentation Platform', 'category': 'platforms', 'tags': ['experiment', 'platform', 'analytics']},
    {'id': 'prod_007', 'name': 'SDK Integration Kit', 'category': 'kits', 'tags': ['sdk', 'integration', 'developer']},
    {'id': 'prod_008', 'name': 'Release Automation', 'category': 'platforms', 'tags': ['release', 'automation', 'cicd']},
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
# SEARCH ROUTES
# ============================================================================

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': SERVICE_NAME,
        'version': SERVICE_VERSION,
    })


@app.route('/search', methods=['POST'])
def search():
    """Search products."""
    with start_span('search.query') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)
        
        maybe_raise_error(SERVICE_NAME, '/search')
        
        data = request.get_json() or {}
        query = data.get('query', '').lower()
        category = data.get('category')
        limit = data.get('limit', 10)
        
        span.set_attribute('query', query)
        span.set_attribute('category', category or 'all')
        span.set_attribute('limit', limit)
        
        # Simulate search processing
        time.sleep(0.15)
        
        # Filter results
        results = []
        for item in SEARCH_DATA:
            if query:
                if query in item['name'].lower() or any(query in tag for tag in item['tags']):
                    if not category or item['category'] == category:
                        results.append(item)
            elif category:
                if item['category'] == category:
                    results.append(item)
            else:
                results.append(item)
        
        results = results[:limit]
        
        record_log(f"Search query: '{query}' returned {len(results)} results", LEVELS['info'], {
            **get_common_attributes(SERVICE_NAME, '/search'),
            'query': query,
            'result_count': len(results),
            'category': category,
        })
        
        # Enrich results with stock info from inventory service
        try:
            for result in results:
                inventory_resp = call_service('inventory-service', f"/products/{result['id']}")
                if inventory_resp.get('success'):
                    result['stock'] = inventory_resp.get('product', {}).get('stock', 0)
                    result['price'] = inventory_resp.get('product', {}).get('price', 0)
        except Exception as e:
            record_log(f"Failed to enrich search results with inventory data: {e}", LEVELS['warning'],
                       get_common_attributes(SERVICE_NAME, '/search'))
        
        return jsonify({
            'success': True,
            'service': SERVICE_NAME,
            'query': query,
            'results': results,
            'total': len(results),
        })


@app.route('/query', methods=['POST'])
def query():
    """Alternative query endpoint."""
    with start_span('search.alternative_query') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)
        
        maybe_raise_error(SERVICE_NAME, '/query')
        
        data = request.get_json() or {}
        query_string = data.get('q', '')
        
        time.sleep(0.1)
        
        # Simple search
        results = [item for item in SEARCH_DATA if query_string.lower() in item['name'].lower()]
        
        return jsonify({
            'success': True,
            'service': SERVICE_NAME,
            'results': results,
        })


@app.route('/suggest', methods=['GET'])
def suggest():
    """Get search suggestions."""
    with start_span('search.suggest') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)
        
        prefix = request.args.get('q', '').lower()
        
        time.sleep(0.05)
        
        # Generate suggestions based on prefix
        suggestions = []
        for item in SEARCH_DATA:
            if prefix in item['name'].lower():
                suggestions.append(item['name'])
            for tag in item['tags']:
                if prefix in tag and tag not in suggestions:
                    suggestions.append(tag)
        
        return jsonify({
            'success': True,
            'service': SERVICE_NAME,
            'suggestions': suggestions[:5],
        })


@app.route('/categories', methods=['GET'])
def list_categories():
    """List all categories."""
    categories = list(set(item['category'] for item in SEARCH_DATA))
    
    return jsonify({
        'success': True,
        'service': SERVICE_NAME,
        'categories': categories,
    })


@app.route('/popular', methods=['GET'])
def popular_searches():
    """Get popular searches."""
    with start_span('search.popular') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)
        
        time.sleep(0.08)
        
        popular = [
            {'query': 'feature flags', 'count': 1250},
            {'query': 'rollout', 'count': 980},
            {'query': 'testing', 'count': 750},
            {'query': 'targeting', 'count': 620},
            {'query': 'sdk', 'count': 450},
        ]
        
        return jsonify({
            'success': True,
            'service': SERVICE_NAME,
            'popular': popular,
        })


@app.route('/', methods=['GET'])
def root():
    """Root endpoint."""
    return jsonify({
        'service': SERVICE_NAME,
        'version': SERVICE_VERSION,
        'endpoints': ['/health', '/search', '/query', '/suggest', '/categories', '/popular']
    })


if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5008))
    print(f"\n🚀 Starting {SERVICE_NAME} on http://localhost:{port}")
    app.run(debug=True, host='0.0.0.0', port=port)

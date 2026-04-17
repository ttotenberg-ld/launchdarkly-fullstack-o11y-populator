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
from dotenv import load_dotenv

from ldobserve.observe import record_log, record_exception, start_span, LEVELS

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from shared.observability import create_ld_client, get_common_attributes, setup_flask_instrumentation
from shared.db import get_engine, install_trace_attributes

from shared.service_names import get_service_url
from sqlalchemy import text

# Load environment variables
load_dotenv()

# Service configuration
SERVICE_NAME = os.getenv('SERVICE_NAME', 'search-service')
SERVICE_VERSION = os.getenv('SERVICE_VERSION', '1.0.0')
USE_DOCKER = os.getenv('USE_DOCKER', 'true').lower() == 'true'

# IMPORTANT: Initialize LaunchDarkly FIRST to set up tracer provider
client = create_ld_client(SERVICE_NAME, SERVICE_VERSION)

# Initialize Flask app
app = Flask(__name__)
CORS(app, expose_headers=['traceparent', 'tracestate'], allow_headers=['Content-Type', 'traceparent', 'tracestate'])

# Set up instrumentation AFTER LD client is initialized
setup_flask_instrumentation(app)

# Search reads from inventorydb directly — different service, same DB: the
# cross-service DB-level dependency shows up cleanly in traces.
engine = get_engine(default_db='inventorydb')
install_trace_attributes(engine, SERVICE_NAME)

# Fallback in-memory data — only used if the DB is unreachable on a given
# request. Keeps /suggest, /categories etc. functional in degraded mode.
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


def _row_to_product(row) -> dict:
    return {
        'id':       row.id,
        'name':     row.name,
        'category': row.category,
        'tags':     list(row.tags or []),
        'price':    (row.price_cents or 0) / 100,
        'stock':    int(row.stock) if row.stock is not None else 0,
    }


def db_search_products(query: str, category: str | None, limit: int) -> list[dict]:
    """Full-text-ish LIKE search with inventory join.

    products.name has no index, so ILIKE '%foo%' is a deliberate seq scan —
    that's visible in the span attributes when SQL queries get expensive.
    """
    params: dict = {'limit': limit}
    where = []

    if query:
        params['q'] = f"%{query}%"
        # Search name OR tags. `ANY` on a TEXT[] column handles the tag match.
        where.append("(p.name ILIKE :q OR EXISTS (SELECT 1 FROM unnest(p.tags) t WHERE t ILIKE :q))")
    if category:
        params['category'] = category
        where.append("p.category = :category")

    where_sql = ('WHERE ' + ' AND '.join(where)) if where else ''
    sql = f"""
        SELECT p.id, p.name, p.category, p.tags, p.price_cents, i.stock
        FROM products p
        LEFT JOIN inventory i ON i.product_id = p.id
        {where_sql}
        ORDER BY p.id
        LIMIT :limit
    """
    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).fetchall()
    return [_row_to_product(r) for r in rows]


def db_suggest(prefix: str, limit: int = 5) -> list[str]:
    if not prefix:
        return []
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT name
                FROM products
                WHERE name ILIKE :q
                ORDER BY name
                LIMIT :limit
            """),
            {'q': f"%{prefix}%", 'limit': limit},
        ).fetchall()
    return [r.name for r in rows]


def db_categories() -> list[str]:
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT DISTINCT category FROM products ORDER BY category")).fetchall()
    return [r.category for r in rows]


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

        data = request.get_json() or {}
        query = data.get('query', '')
        category = data.get('category')
        limit = int(data.get('limit', 10))

        span.set_attribute('query', query)
        span.set_attribute('category', category or 'all')
        span.set_attribute('limit', limit)

        results = db_search_products(query, category, limit)

        record_log(f"Search query: '{query}' returned {len(results)} results", LEVELS['info'], {
            **get_common_attributes(SERVICE_NAME, '/search'),
            'query': query,
            'result_count': len(results),
            'category': category,
        })

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

        data = request.get_json() or {}
        query_string = data.get('q', '')
        span.set_attribute('query', query_string)

        results = db_search_products(query_string, None, 25)

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

        prefix = request.args.get('q', '')
        span.set_attribute('prefix', prefix)

        suggestions = db_suggest(prefix, limit=5)

        return jsonify({
            'success': True,
            'service': SERVICE_NAME,
            'suggestions': suggestions,
        })


@app.route('/categories', methods=['GET'])
def list_categories():
    """List all categories."""
    with start_span('search.categories') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)

        categories = db_categories()

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
    app.run(debug=False, host='0.0.0.0', port=port)

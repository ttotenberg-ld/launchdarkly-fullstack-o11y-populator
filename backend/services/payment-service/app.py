"""
Payment Service - Payment processing and validation.
Port: 5004
"""

import os
import time
import uuid
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
CORS(app, expose_headers=['traceparent', 'tracestate'], allow_headers=['Content-Type', 'traceparent', 'tracestate'])
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()

# Service configuration
SERVICE_NAME = os.getenv('SERVICE_NAME', 'payment-service')
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
# PAYMENT ROUTES
# ============================================================================

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': SERVICE_NAME,
        'version': SERVICE_VERSION,
    })


@app.route('/process', methods=['POST'])
def process_payment():
    """Process a payment."""
    with start_span('payment.process') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)
        
        # This is where errors are often injected in the trace chain
        maybe_raise_error(SERVICE_NAME, '/process')
        
        data = request.get_json() or {}
        order_id = data.get('order_id', f"ord_{uuid.uuid4().hex[:12]}")
        amount = data.get('amount', random.uniform(20, 200))
        currency = data.get('currency', 'USD')
        user = data.get('user', {})
        
        transaction_id = f"txn_{uuid.uuid4().hex[:12]}"
        
        span.set_attribute('order_id', order_id)
        span.set_attribute('amount', amount)
        span.set_attribute('currency', currency)
        span.set_attribute('transaction_id', transaction_id)
        
        record_log(f"Processing payment for order {order_id}", LEVELS['info'], {
            **get_common_attributes(SERVICE_NAME, '/process'),
            'order_id': order_id,
            'amount': amount,
            'currency': currency,
            'provider': 'stripe',
        })
        
        # Step 1: Validate card
        with start_span('payment.validate_card') as val_span:
            val_span.set_attribute('service', SERVICE_NAME)
            val_span.set_attribute('step', 'validate_card')
            
            maybe_raise_error(SERVICE_NAME, '/validate')
            
            # Simulate card validation
            time.sleep(0.3)
            val_span.set_attribute('card.valid', True)
        
        # Step 2: Fraud check
        with start_span('payment.fraud_check') as fraud_span:
            fraud_span.set_attribute('service', SERVICE_NAME)
            fraud_span.set_attribute('step', 'fraud_check')
            
            # Simulate fraud detection
            time.sleep(0.2)
            fraud_score = random.uniform(0, 0.3)  # Low risk
            fraud_span.set_attribute('fraud_score', fraud_score)
            
            record_log(f"Fraud check passed for transaction {transaction_id}", LEVELS['debug'], {
                **get_common_attributes(SERVICE_NAME, '/process'),
                'transaction_id': transaction_id,
                'fraud_score': fraud_score,
            })
        
        # Step 3: Charge card
        with start_span('payment.charge') as charge_span:
            charge_span.set_attribute('service', SERVICE_NAME)
            charge_span.set_attribute('step', 'charge')
            
            # Simulate payment gateway call
            time.sleep(0.4)
            charge_span.set_attribute('charge.success', True)
        
        record_log(f"Payment successful for order {order_id}", LEVELS['info'], {
            **get_common_attributes(SERVICE_NAME, '/process'),
            'order_id': order_id,
            'transaction_id': transaction_id,
            'amount': amount,
            'status': 'completed',
        })
        
        # Send receipt notification
        try:
            call_service('notification-service', '/send', 'POST', {
                'type': 'email',
                'template': 'payment_receipt',
                'user': user,
                'transaction_id': transaction_id,
                'amount': amount,
            })
        except Exception as e:
            record_log(f"Failed to send payment receipt: {e}", LEVELS['warning'],
                       get_common_attributes(SERVICE_NAME, '/process'))
        
        return jsonify({
            'success': True,
            'service': SERVICE_NAME,
            'transaction': {
                'id': transaction_id,
                'order_id': order_id,
                'amount': amount,
                'currency': currency,
                'status': 'completed',
                'provider': 'stripe',
            }
        })


@app.route('/refund', methods=['POST'])
def refund_payment():
    """Process a refund."""
    with start_span('payment.refund') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)
        
        data = request.get_json() or {}
        transaction_id = data.get('transaction_id', f"txn_{uuid.uuid4().hex[:12]}")
        amount = data.get('amount', random.uniform(20, 200))
        
        refund_id = f"ref_{uuid.uuid4().hex[:12]}"
        
        span.set_attribute('transaction_id', transaction_id)
        span.set_attribute('refund_id', refund_id)
        span.set_attribute('amount', amount)
        
        # Simulate refund processing
        time.sleep(0.5)
        
        record_log(f"Refund processed for transaction {transaction_id}", LEVELS['info'], {
            **get_common_attributes(SERVICE_NAME, '/refund'),
            'transaction_id': transaction_id,
            'refund_id': refund_id,
            'amount': amount,
        })
        
        return jsonify({
            'success': True,
            'service': SERVICE_NAME,
            'refund': {
                'id': refund_id,
                'transaction_id': transaction_id,
                'amount': amount,
                'status': 'completed',
            }
        })


@app.route('/balance', methods=['GET'])
def get_balance():
    """Get account balance."""
    with start_span('payment.balance') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)
        
        time.sleep(0.1)
        
        return jsonify({
            'success': True,
            'service': SERVICE_NAME,
            'balance': {
                'available': 125000.50,
                'pending': 3500.00,
                'currency': 'USD',
            }
        })


@app.route('/', methods=['GET'])
def root():
    """Root endpoint."""
    return jsonify({
        'service': SERVICE_NAME,
        'version': SERVICE_VERSION,
        'endpoints': ['/health', '/process', '/refund', '/balance']
    })


if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5004))
    print(f"\n🚀 Starting {SERVICE_NAME} on http://localhost:{port}")
    app.run(debug=True, host='0.0.0.0', port=port)

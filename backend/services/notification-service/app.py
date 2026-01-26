"""
Notification Service - Email, push, SMS notifications.
Port: 5006
"""

import os
import time
import uuid
import random
from flask import Flask, jsonify, request
from flask_cors import CORS
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from dotenv import load_dotenv

from ldobserve.observe import record_log, record_exception, start_span, LEVELS

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from shared.observability import create_ld_client, get_common_attributes
from shared.error_injection import maybe_raise_error, InjectedError

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)
FlaskInstrumentor().instrument_app(app)

# Service configuration
SERVICE_NAME = os.getenv('SERVICE_NAME', 'notification-service')
SERVICE_VERSION = os.getenv('SERVICE_VERSION', '1.0.0')

# Initialize LaunchDarkly
client = create_ld_client(SERVICE_NAME, SERVICE_VERSION)

# Email templates
EMAIL_TEMPLATES = {
    'order_confirmation': {
        'subject': 'Order Confirmation - #{order_id}',
        'body': 'Thank you for your order! Your order #{order_id} has been confirmed.',
    },
    'payment_receipt': {
        'subject': 'Payment Receipt - ${amount}',
        'body': 'Your payment of ${amount} has been processed successfully.',
    },
    'profile_updated': {
        'subject': 'Profile Updated',
        'body': 'Your profile has been updated successfully.',
    },
    'password_reset': {
        'subject': 'Password Reset Request',
        'body': 'Click here to reset your password.',
    },
    'welcome': {
        'subject': 'Welcome to LaunchDarkly Demo!',
        'body': 'Thank you for signing up!',
    },
    'low_stock_alert': {
        'subject': 'Low Stock Alert - {product_id}',
        'body': 'Product {product_id} is running low on stock.',
    },
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
# NOTIFICATION ROUTES
# ============================================================================

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': SERVICE_NAME,
        'version': SERVICE_VERSION,
    })


@app.route('/send', methods=['POST'])
def send_notification():
    """Send a notification."""
    with start_span('notification.send') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)
        
        maybe_raise_error(SERVICE_NAME, '/send')
        
        data = request.get_json() or {}
        notification_type = data.get('type', 'email')
        template = data.get('template', 'welcome')
        user = data.get('user', {})
        
        notification_id = f"ntf_{uuid.uuid4().hex[:12]}"
        
        span.set_attribute('notification_id', notification_id)
        span.set_attribute('notification_type', notification_type)
        span.set_attribute('template', template)
        
        # Simulate sending notification
        if notification_type == 'email':
            time.sleep(0.3)  # Email takes longer
        elif notification_type == 'push':
            time.sleep(0.1)
        else:
            time.sleep(0.2)
        
        template_data = EMAIL_TEMPLATES.get(template, EMAIL_TEMPLATES['welcome'])
        
        record_log(f"Notification sent: {notification_type} using template '{template}'", LEVELS['info'], {
            **get_common_attributes(SERVICE_NAME, '/send'),
            'notification_id': notification_id,
            'notification_type': notification_type,
            'template': template,
            'recipient': user.get('email', 'unknown'),
        })
        
        return jsonify({
            'success': True,
            'service': SERVICE_NAME,
            'notification': {
                'id': notification_id,
                'type': notification_type,
                'template': template,
                'subject': template_data.get('subject'),
                'status': 'sent',
                'sent_at': time.time(),
            }
        })


@app.route('/email', methods=['POST'])
def send_email():
    """Send an email notification."""
    with start_span('notification.email') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)
        
        maybe_raise_error(SERVICE_NAME, '/email')
        
        data = request.get_json() or {}
        to = data.get('to', 'user@example.com')
        subject = data.get('subject', 'Notification')
        body = data.get('body', '')
        
        email_id = f"eml_{uuid.uuid4().hex[:12]}"
        
        span.set_attribute('email_id', email_id)
        span.set_attribute('to', to)
        
        # Simulate SMTP sending
        time.sleep(0.4)
        
        record_log(f"Email sent to {to}", LEVELS['info'], {
            **get_common_attributes(SERVICE_NAME, '/email'),
            'email_id': email_id,
            'to': to,
            'subject': subject,
        })
        
        return jsonify({
            'success': True,
            'service': SERVICE_NAME,
            'email': {
                'id': email_id,
                'to': to,
                'subject': subject,
                'status': 'delivered',
            }
        })


@app.route('/push', methods=['POST'])
def send_push():
    """Send a push notification."""
    with start_span('notification.push') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)
        
        data = request.get_json() or {}
        user_key = data.get('user_key', 'unknown')
        title = data.get('title', 'Notification')
        body = data.get('body', '')
        
        push_id = f"psh_{uuid.uuid4().hex[:12]}"
        
        # Simulate push sending
        time.sleep(0.15)
        
        record_log(f"Push notification sent to user {user_key}", LEVELS['info'], {
            **get_common_attributes(SERVICE_NAME, '/push'),
            'push_id': push_id,
            'user_key': user_key,
        })
        
        return jsonify({
            'success': True,
            'service': SERVICE_NAME,
            'push': {
                'id': push_id,
                'user_key': user_key,
                'title': title,
                'status': 'delivered',
            }
        })


@app.route('/sms', methods=['POST'])
def send_sms():
    """Send an SMS notification."""
    with start_span('notification.sms') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', SERVICE_NAME)
        
        data = request.get_json() or {}
        phone = data.get('phone', '+1234567890')
        message = data.get('message', '')
        
        sms_id = f"sms_{uuid.uuid4().hex[:12]}"
        
        # Simulate SMS sending
        time.sleep(0.25)
        
        record_log(f"SMS sent to {phone}", LEVELS['info'], {
            **get_common_attributes(SERVICE_NAME, '/sms'),
            'sms_id': sms_id,
            'phone': phone[:6] + '****',  # Mask phone number
        })
        
        return jsonify({
            'success': True,
            'service': SERVICE_NAME,
            'sms': {
                'id': sms_id,
                'phone': phone[:6] + '****',
                'status': 'delivered',
            }
        })


@app.route('/templates', methods=['GET'])
def list_templates():
    """List available notification templates."""
    return jsonify({
        'success': True,
        'service': SERVICE_NAME,
        'templates': list(EMAIL_TEMPLATES.keys()),
    })


@app.route('/', methods=['GET'])
def root():
    """Root endpoint."""
    return jsonify({
        'service': SERVICE_NAME,
        'version': SERVICE_VERSION,
        'endpoints': ['/health', '/send', '/email', '/push', '/sms', '/templates']
    })


if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5006))
    print(f"\n🚀 Starting {SERVICE_NAME} on http://localhost:{port}")
    app.run(debug=True, host='0.0.0.0', port=port)

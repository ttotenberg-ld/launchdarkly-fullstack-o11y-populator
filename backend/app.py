import os
import time
import asyncio
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
import ldclient
from ldclient.config import Config

import ldobserve
from ldobserve import ObservabilityConfig, ObservabilityPlugin, observe

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# LaunchDarkly Configuration
sdk_key = os.getenv('LD_SDK_KEY', 'sdk-key-123abc')
service_name = os.getenv('SERVICE_NAME', 'python-observability-demo')
service_version = os.getenv('SERVICE_VERSION', '1.0.0')
environment = os.getenv('ENVIRONMENT', 'development')

# Initialize LaunchDarkly with Observability Plugin
observability_config = ObservabilityConfig(
    service_name=service_name,
    service_version=service_version,
    environment=environment
)

plugin = ObservabilityPlugin(observability_config)

config = Config(
    sdk_key=sdk_key,
    plugins=[plugin]
)

ldclient.set_config(config)
client = ldclient.get()

print(f"✓ LaunchDarkly Python SDK initialized with observability")
print(f"  Service: {service_name}")
print(f"  Version: {service_version}")
print(f"  Environment: {environment}")

# Default LaunchDarkly context for flag evaluations
default_context = {
    "kind": "user",
    "key": "demo-user",
    "name": "Demo User"
}


# ============================================================================
# ERROR ENDPOINTS
# ============================================================================

@app.route('/api/errors/manual', methods=['GET'])
@observe(name='error.manual')
def error_manual():
    """Generate and record a manual error"""
    try:
        # Simulate a deliberate error
        raise ValueError("This is a manually triggered error for demonstration")
    except Exception as error:
        # Record error to LaunchDarkly observability
        ldobserve.record_error(
            error,
            'Manual error triggered from API endpoint',
            {
                'endpoint': '/api/errors/manual',
                'method': 'GET',
                'demo_type': 'manual_error'
            }
        )
        
        return jsonify({
            'success': True,
            'message': 'Manual error recorded successfully',
            'error_type': type(error).__name__,
            'error_message': str(error)
        }), 200


@app.route('/api/errors/async', methods=['GET'])
@observe(name='error.async')
def error_async():
    """Generate an async error with delay"""
    try:
        # Simulate async operation with delay
        time.sleep(1)
        
        # Simulate an error in async operation
        raise RuntimeError("Async operation failed after 1 second delay")
    except Exception as error:
        # Record error to LaunchDarkly observability
        ldobserve.record_error(
            error,
            'Async operation error',
            {
                'endpoint': '/api/errors/async',
                'method': 'GET',
                'demo_type': 'async_error',
                'delay_seconds': 1
            }
        )
        
        return jsonify({
            'success': True,
            'message': 'Async error recorded successfully',
            'error_type': type(error).__name__,
            'error_message': str(error)
        }), 200


@app.route('/api/errors/uncaught', methods=['GET'])
@observe(name='error.uncaught')
def error_uncaught():
    """Generate an uncaught exception (will be caught by Flask error handler)"""
    # This will raise an uncaught exception
    raise Exception("This is an uncaught exception for demonstration")


# Global error handler for uncaught exceptions
@app.errorhandler(Exception)
def handle_exception(error):
    """Global error handler that records all uncaught exceptions"""
    ldobserve.record_error(
        error,
        'Uncaught exception in Flask application',
        {
            'error_type': type(error).__name__,
            'demo_type': 'uncaught_error'
        }
    )
    
    return jsonify({
        'success': True,
        'message': 'Uncaught error recorded successfully',
        'error_type': type(error).__name__,
        'error_message': str(error)
    }), 200


# ============================================================================
# LOGGING ENDPOINTS
# ============================================================================

@app.route('/api/logs/debug', methods=['GET'])
@observe(name='log.debug')
def log_debug():
    """Record a debug log"""
    ldobserve.record_log('Debug log message from Python backend', 'debug', {
        'endpoint': '/api/logs/debug',
        'timestamp': time.time()
    })
    
    return jsonify({
        'success': True,
        'message': 'Debug log recorded',
        'severity': 'debug'
    })


@app.route('/api/logs/info', methods=['GET'])
@observe(name='log.info')
def log_info():
    """Record an info log"""
    ldobserve.record_log('Info log message from Python backend', 'info', {
        'endpoint': '/api/logs/info',
        'timestamp': time.time()
    })
    
    return jsonify({
        'success': True,
        'message': 'Info log recorded',
        'severity': 'info'
    })


@app.route('/api/logs/warn', methods=['GET'])
@observe(name='log.warn')
def log_warn():
    """Record a warning log"""
    ldobserve.record_log('Warning log message from Python backend', 'warn', {
        'endpoint': '/api/logs/warn',
        'timestamp': time.time()
    })
    
    return jsonify({
        'success': True,
        'message': 'Warning log recorded',
        'severity': 'warn'
    })


@app.route('/api/logs/error', methods=['GET'])
@observe(name='log.error')
def log_error():
    """Record an error log"""
    ldobserve.record_log('Error log message from Python backend', 'error', {
        'endpoint': '/api/logs/error',
        'timestamp': time.time()
    })
    
    return jsonify({
        'success': True,
        'message': 'Error log recorded',
        'severity': 'error'
    })


# ============================================================================
# TRACING ENDPOINTS
# ============================================================================

@app.route('/api/traces/simple', methods=['POST'])
@observe(name='trace.simple')
def trace_simple():
    """Create an automatic span for a simple operation"""
    
    # Use automatic span - it ends when the function completes
    with ldobserve.start_span('api.fetch.simple') as span:
        span.set_attribute('operation.type', 'simple_fetch')
        span.set_attribute('timestamp', time.time())
        
        # Simulate API processing with delay
        time.sleep(0.8)
        
        # Simulated response data
        simulated_data = {
            'id': 1,
            'title': 'Getting Started with LaunchDarkly Python Observability',
            'userId': 1
        }
        
        span.set_attribute('response.status', 200)
        span.set_attribute('response.title', simulated_data['title'])
        
        return jsonify({
            'success': True,
            'message': f'✓ Fetched: "{simulated_data["title"]}"',
            'data': simulated_data
        })


@app.route('/api/traces/multi-step', methods=['POST'])
@observe(name='trace.multi_step')
def trace_multi_step():
    """Create a manual span with multiple steps"""
    
    completed_steps = 0
    steps = []
    
    # Use manual span - we control when it ends
    with ldobserve.start_manual_span('workflow.multi_step') as span:
        try:
            span.set_attribute('operation.type', 'multi_step_workflow')
            span.set_attribute('workflow.total_steps', 3)
            
            # Step 1: First operation
            time.sleep(0.6)
            completed_steps = 1
            span.set_attribute('step.1.completed', True)
            span.set_attribute('step.1.timestamp', time.time())
            steps.append({'step': 1, 'status': 'completed', 'message': 'Step 1/3: First operation complete'})
            
            # Step 2: Second operation
            time.sleep(0.6)
            completed_steps = 2
            span.set_attribute('step.2.completed', True)
            span.set_attribute('step.2.timestamp', time.time())
            steps.append({'step': 2, 'status': 'completed', 'message': 'Step 2/3: Second operation complete'})
            
            # Step 3: Final operation
            time.sleep(0.6)
            completed_steps = 3
            span.set_attribute('step.3.completed', True)
            span.set_attribute('step.3.timestamp', time.time())
            span.set_attribute('workflow.success', True)
            steps.append({'step': 3, 'status': 'completed', 'message': 'Step 3/3: Final operation complete'})
            
            span.set_status_ok()
            
            return jsonify({
                'success': True,
                'message': f'✓ Completed {completed_steps}/3 steps!',
                'completed_steps': completed_steps,
                'total_steps': 3,
                'steps': steps
            })
            
        except Exception as error:
            span.set_status_error(str(error))
            
            # Record error
            ldobserve.record_error(error, 'Multi-step workflow failed', {
                'endpoint': '/api/traces/multi-step',
                'completed_steps': completed_steps
            })
            
            return jsonify({
                'success': False,
                'message': f'✗ Error after {completed_steps}/3 steps: {str(error)}',
                'completed_steps': completed_steps,
                'total_steps': 3,
                'error': str(error)
            }), 500


# ============================================================================
# FEATURE FLAG DEMO ENDPOINT
# ============================================================================

@app.route('/api/feature-demo', methods=['GET'])
@observe(name='feature.demo')
def feature_demo():
    """Demonstrate feature flag integration"""
    
    # Evaluate feature flag
    flag_value = client.variation('pythonDemoFeature', default_context, False)
    
    # Log flag evaluation
    ldobserve.record_log(
        f'Feature flag "pythonDemoFeature" evaluated to: {flag_value}',
        'info',
        {
            'flag_key': 'pythonDemoFeature',
            'flag_value': flag_value,
            'user_key': default_context['key']
        }
    )
    
    if flag_value:
        # Enhanced response when flag is enabled
        return jsonify({
            'success': True,
            'feature_enabled': True,
            'message': '🎉 Feature flag is ENABLED!',
            'data': {
                'status': 'enhanced',
                'features': [
                    'Advanced analytics',
                    'Premium support',
                    'Custom integrations'
                ],
                'timestamp': time.time()
            }
        })
    else:
        # Basic response when flag is disabled
        return jsonify({
            'success': True,
            'feature_enabled': False,
            'message': 'Feature flag is disabled',
            'data': {
                'status': 'basic',
                'timestamp': time.time()
            }
        })


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': service_name,
        'version': service_version,
        'environment': environment,
        'launchdarkly': 'connected' if client.is_initialized() else 'initializing'
    })


@app.route('/', methods=['GET'])
def root():
    """Root endpoint"""
    return jsonify({
        'message': 'LaunchDarkly Python Observability Demo API',
        'service': service_name,
        'version': service_version,
        'endpoints': {
            'errors': ['/api/errors/manual', '/api/errors/async', '/api/errors/uncaught'],
            'logs': ['/api/logs/debug', '/api/logs/info', '/api/logs/warn', '/api/logs/error'],
            'traces': ['/api/traces/simple', '/api/traces/multi-step'],
            'features': ['/api/feature-demo'],
            'health': ['/api/health']
        }
    })


if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5000))
    print(f"\n🚀 Starting Flask server on http://localhost:{port}")
    print(f"📊 Observability data will be sent to LaunchDarkly\n")
    app.run(debug=True, host='0.0.0.0', port=port)


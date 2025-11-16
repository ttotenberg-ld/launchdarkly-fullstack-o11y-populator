# LaunchDarkly Python Observability Backend

Flask API demonstrating LaunchDarkly's Python observability features including error tracking, logging, distributed tracing, and feature flags.

## Features

- **Error Recording**: Manual, async, and uncaught exception handling
- **Structured Logging**: Multi-level logging with context and metadata
- **Distributed Tracing**: Automatic and manual spans with OpenTelemetry
- **Feature Flags**: Server-side flag evaluation and logging
- **CORS Enabled**: Configured for frontend communication

## Prerequisites

- Python 3.10 or higher
- pip (Python package installer)
- A LaunchDarkly account with server-side SDK key

## Installation

### 1. Create Virtual Environment

```bash
python -m venv venv
```

### 2. Activate Virtual Environment

**macOS/Linux:**
```bash
source venv/bin/activate
```

**Windows:**
```bash
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and add your configuration:

```bash
# LaunchDarkly SDK Key (server-side)
# Get from: LaunchDarkly Dashboard > Project Settings > Environments > SDK Key
LD_SDK_KEY=your-sdk-key-here

# Observability Configuration
SERVICE_NAME=python-observability-demo
SERVICE_VERSION=1.0.0
ENVIRONMENT=development

# Flask Configuration
FLASK_ENV=development
FLASK_PORT=5000
```

## Running the Server

### Development Mode

```bash
python app.py
```

The server will start on http://localhost:5000 with auto-reload enabled.

### Production Mode

```bash
export FLASK_ENV=production
python app.py
```

## API Endpoints

### Root
- `GET /` - API information and endpoint list

### Health Check
- `GET /api/health` - Health check with LaunchDarkly connection status

### Error Tracking Endpoints

#### `GET /api/errors/manual`
Generates and records a manual error.

**Response:**
```json
{
  "success": true,
  "message": "Manual error recorded successfully",
  "error_type": "ValueError",
  "error_message": "This is a manually triggered error for demonstration"
}
```

#### `GET /api/errors/async`
Generates an async error with a 1-second delay.

**Response:**
```json
{
  "success": true,
  "message": "Async error recorded successfully",
  "error_type": "RuntimeError",
  "error_message": "Async operation failed after 1 second delay"
}
```

#### `GET /api/errors/uncaught`
Generates an uncaught exception (handled by global error handler).

**Response:**
```json
{
  "success": true,
  "message": "Uncaught error recorded successfully",
  "error_type": "Exception",
  "error_message": "This is an uncaught exception for demonstration"
}
```

### Logging Endpoints

All logging endpoints record logs at different severity levels:

#### `GET /api/logs/debug`
Records a debug-level log.

#### `GET /api/logs/info`
Records an info-level log.

#### `GET /api/logs/warn`
Records a warning-level log.

#### `GET /api/logs/error`
Records an error-level log.

**Response (all endpoints):**
```json
{
  "success": true,
  "message": "Debug log recorded",
  "severity": "debug"
}
```

### Tracing Endpoints

#### `POST /api/traces/simple`
Creates an automatic span for a simple operation (0.8s duration).

**Response:**
```json
{
  "success": true,
  "message": "✓ Fetched: \"Getting Started with LaunchDarkly Python Observability\"",
  "data": {
    "id": 1,
    "title": "Getting Started with LaunchDarkly Python Observability",
    "userId": 1
  }
}
```

#### `POST /api/traces/multi-step`
Creates a manual span with 3 tracked steps (1.8s total duration).

**Response:**
```json
{
  "success": true,
  "message": "✓ Completed 3/3 steps!",
  "completed_steps": 3,
  "total_steps": 3,
  "steps": [
    {"step": 1, "status": "completed", "message": "Step 1/3: First operation complete"},
    {"step": 2, "status": "completed", "message": "Step 2/3: Second operation complete"},
    {"step": 3, "status": "completed", "message": "Step 3/3: Final operation complete"}
  ]
}
```

### Feature Flag Demo

#### `GET /api/feature-demo`
Demonstrates feature flag integration. Returns different responses based on the `pythonDemoFeature` flag.

**Response (flag enabled):**
```json
{
  "success": true,
  "feature_enabled": true,
  "message": "🎉 Feature flag is ENABLED!",
  "data": {
    "status": "enhanced",
    "features": ["Advanced analytics", "Premium support", "Custom integrations"],
    "timestamp": 1234567890.123
  }
}
```

**Response (flag disabled):**
```json
{
  "success": true,
  "feature_enabled": false,
  "message": "Feature flag is disabled",
  "data": {
    "status": "basic",
    "timestamp": 1234567890.123
  }
}
```

## Code Examples

### Initializing LaunchDarkly with Observability

```python
from ldobserve import ObservabilityConfig, ObservabilityPlugin
import ldclient
from ldclient.config import Config

# Create observability configuration
observability_config = ObservabilityConfig(
    service_name='python-observability-demo',
    service_version='1.0.0',
    environment='development'
)

# Create observability plugin
plugin = ObservabilityPlugin(observability_config)

# Configure LaunchDarkly SDK
config = Config(
    sdk_key='your-sdk-key',
    plugins=[plugin]
)

ldclient.set_config(config)
client = ldclient.get()
```

### Recording Errors

```python
import ldobserve

try:
    # Some operation that might fail
    result = risky_operation()
except Exception as error:
    # Record error to LaunchDarkly
    ldobserve.record_error(
        error,
        'Operation failed',
        {
            'operation': 'risky_operation',
            'user_id': 123,
            'context': 'additional_info'
        }
    )
    # Handle error appropriately
```

### Recording Logs

```python
import ldobserve

# Debug log
ldobserve.record_log('Debug message', 'debug', {'context': 'value'})

# Info log
ldobserve.record_log('User logged in', 'info', {'user_id': 123})

# Warning log
ldobserve.record_log('Rate limit approaching', 'warn', {'usage': '90%'})

# Error log
ldobserve.record_log('Operation failed', 'error', {'error_code': 'E123'})
```

### Creating Traces

#### Automatic Span

```python
import ldobserve

with ldobserve.start_span('database.query') as span:
    span.set_attribute('query_type', 'SELECT')
    span.set_attribute('table', 'users')
    
    # Perform operation
    result = db.query('SELECT * FROM users')
    
    span.set_attribute('row_count', len(result))
    # Span ends automatically when context exits
```

#### Manual Span with Multiple Steps

```python
import ldobserve

with ldobserve.start_manual_span('workflow.checkout') as span:
    try:
        span.set_attribute('workflow.total_steps', 3)
        
        # Step 1: Validate cart
        span.set_attribute('step.1.name', 'validate_cart')
        validate_cart(cart)
        span.set_attribute('step.1.completed', True)
        
        # Step 2: Process payment
        span.set_attribute('step.2.name', 'process_payment')
        process_payment(payment_info)
        span.set_attribute('step.2.completed', True)
        
        # Step 3: Create order
        span.set_attribute('step.3.name', 'create_order')
        order = create_order(cart, payment_info)
        span.set_attribute('step.3.completed', True)
        
        span.set_status_ok()
        return order
        
    except Exception as error:
        span.set_status_error(str(error))
        ldobserve.record_error(error, 'Checkout failed')
        raise
```

### Using Feature Flags

```python
# Define user context
context = {
    "kind": "user",
    "key": "user-123",
    "name": "Alice",
    "email": "alice@example.com"
}

# Evaluate flag
flag_value = client.variation('myFeatureFlag', context, False)

if flag_value:
    # Feature enabled
    return enhanced_feature()
else:
    # Feature disabled
    return basic_feature()
```

### Decorator for Automatic Tracing

```python
from ldobserve import observe

@observe(name='api.process_order')
def process_order(order_data):
    """This function will automatically be traced"""
    # Function implementation
    return process_result
```

## Configuration Options

### ObservabilityConfig Parameters

- `service_name` (str): Name of your service (default: 'python-service')
- `service_version` (str): Version of your service (recommended: git SHA)
- `environment` (str): Environment name (e.g., 'production', 'staging', 'development')

### Environment Variables

The observability plugin also respects standard OpenTelemetry environment variables:

- `OTEL_SERVICE_NAME`: Service name (overrides ObservabilityConfig)
- `OTEL_RESOURCE_ATTRIBUTES`: Additional resource attributes
- `OTEL_EXPORTER_OTLP_ENDPOINT`: Custom OTLP endpoint (advanced)

## Viewing Data in LaunchDarkly

After starting the server and making API calls:

1. Log in to LaunchDarkly Dashboard
2. Navigate to **Observability** in the left sidebar
3. View:
   - **Errors**: All recorded errors with full stack traces
   - **Logs**: Structured logs with severity filtering
   - **Traces**: Distributed traces with timing and attributes
   - **Metrics**: Auto-generated metrics from OpenTelemetry data

## Troubleshooting

### SDK Not Initializing

**Symptom**: "LaunchDarkly: initializing" never completes

**Solutions**:
- Verify SDK key is correct
- Check network connectivity
- Ensure firewall allows connections to LaunchDarkly endpoints

### No Observability Data Appearing

**Symptom**: Server runs but no data in LaunchDarkly dashboard

**Solutions**:
- Verify observability features are enabled for your account
- Check that you're viewing the correct project/environment
- Look for errors in server console output
- Ensure SDK initialization completes successfully

### Import Errors

**Symptom**: `ModuleNotFoundError: No module named 'ldobserve'`

**Solutions**:
- Ensure virtual environment is activated
- Run `pip install -r requirements.txt`
- Verify Python version is 3.10 or higher

### CORS Errors from Frontend

**Symptom**: Frontend can't connect due to CORS

**Solutions**:
- Verify `flask-cors` is installed
- Check CORS is enabled in `app.py`
- Ensure frontend is using correct backend URL

## Development Tips

### Adding New Endpoints

1. Define route with `@app.route()`
2. Add `@observe()` decorator for automatic tracing
3. Use `ldobserve.record_error()` for error handling
4. Use `ldobserve.record_log()` for logging
5. Return JSON responses with `jsonify()`

### Testing Locally

```bash
# Test health endpoint
curl http://localhost:5000/api/health

# Test error endpoint
curl http://localhost:5000/api/errors/manual

# Test trace endpoint
curl -X POST http://localhost:5000/api/traces/simple
```

### Best Practices

1. **Always record errors** with context
2. **Use structured logging** with metadata
3. **Add span attributes** for better trace visibility
4. **Log feature flag evaluations** for audit trail
5. **Use meaningful span names** (e.g., `database.query.users` not `query`)

## Dependencies

- `flask>=3.0.0` - Web framework
- `flask-cors>=4.0.0` - CORS support
- `launchdarkly-server-sdk>=9.12.0` - LaunchDarkly Python SDK
- `launchdarkly-observability>=0.1.0` - Observability plugin
- `python-dotenv>=1.0.0` - Environment variable management

## Resources

- [LaunchDarkly Python SDK Observability Docs](https://launchdarkly.com/docs/sdk/observability/python)
- [LaunchDarkly Python SDK Reference](https://launchdarkly-python-sdk.readthedocs.io/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)

## Support

For issues or questions:
- [LaunchDarkly Support](https://support.launchdarkly.com/)
- [LaunchDarkly Community](https://launchdarkly.com/community/)


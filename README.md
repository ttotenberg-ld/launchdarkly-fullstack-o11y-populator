# LaunchDarkly Python Observability Demo

A comprehensive full-stack demonstration of LaunchDarkly's Python observability features, including error tracking, logging, distributed tracing, and feature flags integration.

## Overview

This demo showcases LaunchDarkly's observability capabilities in a realistic full-stack application:

- **Backend**: Python Flask API with LaunchDarkly server-side SDK and observability plugin
- **Frontend**: React application that calls the Python backend
- **Observability**: Comprehensive error tracking, logging, and distributed tracing
- **Feature Flags**: Server-side feature flag integration demonstrating dynamic configuration

## Architecture

```
┌─────────────────┐      HTTP Requests       ┌─────────────────┐
│                 │ ───────────────────────> │                 │
│  React Frontend │                          │  Flask Backend  │
│  (Port 5173)    │ <─────────────────────── │  (Port 5000)    │
│                 │      JSON Responses      │                 │
└─────────────────┘                          └─────────────────┘
        │                                             │
        │                                             │
        │          LaunchDarkly Observability         │
        └──────────────────┬──────────────────────────┘
                           │
                           ▼
                ┌──────────────────────┐
                │   LaunchDarkly       │
                │   Platform           │
                │                      │
                │  • Errors            │
                │  • Logs              │
                │  • Traces            │
                │  • Feature Flags     │
                └──────────────────────┘
```

## Features Demonstrated

### 🐛 Error Tracking
- **Manual Error Recording**: Caught errors with custom context
- **Async Error Handling**: Errors in asynchronous operations
- **Uncaught Exception Handling**: Global error handling
- All errors sent to LaunchDarkly with full context and stack traces

### 📝 Custom Logging
- **Multiple Severity Levels**: Debug, Info, Warning, Error
- **Structured Logging**: Logs with metadata and context
- **Backend Logging**: Server-side log capture and forwarding

### 🔍 Distributed Tracing
- **Automatic Spans**: Simple operations with automatic lifecycle management
- **Manual Spans**: Complex workflows with multiple tracked steps
- **Frontend-to-Backend Tracing**: Full request flow visibility
- **Python Context Managers**: Clean, Pythonic tracing patterns

### 🚩 Feature Flags
- **Server-Side Flags**: Feature toggles in Python backend
- **Dynamic Configuration**: Toggle features without code changes
- **Flag Evaluation Logging**: Track flag usage and variations

## Quick Start

### Prerequisites

- Python 3.10 or higher
- Node.js 16+ and npm
- A LaunchDarkly account with observability features enabled

### 1. Clone and Setup

```bash
# Clone or download this repository
cd launchdarkly-python-o11y-demo
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your LaunchDarkly server-side SDK key
```

**Get your SDK key**: LaunchDarkly Dashboard → Project Settings → Environments → SDK Key

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env and add your LaunchDarkly client-side ID
```

**Get your client-side ID**: LaunchDarkly Dashboard → Project Settings → Environments → Client-side ID

### 4. Run the Application

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate  # If not already activated
python app.py
```

Backend will start on http://localhost:5000

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

Frontend will start on http://localhost:5173

### 5. Use the Demo

1. Open http://localhost:5173 in your browser
2. Click buttons to trigger errors, logs, and traces
3. View observability data in LaunchDarkly Dashboard → Observability section
4. Toggle the `pythonDemoFeature` flag to see backend behavior change

## Project Structure

```
launchdarkly-python-o11y-demo/
├── backend/                    # Python Flask API
│   ├── app.py                 # Main application with all endpoints
│   ├── requirements.txt       # Python dependencies
│   ├── .env.example          # Environment template
│   └── README.md             # Backend documentation
│
├── frontend/                  # React application
│   ├── src/
│   │   ├── components/
│   │   │   ├── ErrorDemo.jsx   # Error tracking UI
│   │   │   ├── LogsDemo.jsx    # Logging UI
│   │   │   ├── TracesDemo.jsx  # Tracing UI
│   │   │   └── ...
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── README.md             # Frontend documentation
│
└── README.md                  # This file
```

## API Endpoints

The Flask backend exposes these endpoints:

### Error Tracking
- `GET /api/errors/manual` - Trigger a manual error
- `GET /api/errors/async` - Trigger an async error with delay
- `GET /api/errors/uncaught` - Trigger an uncaught exception

### Logging
- `GET /api/logs/debug` - Record debug log
- `GET /api/logs/info` - Record info log
- `GET /api/logs/warn` - Record warning log
- `GET /api/logs/error` - Record error log

### Tracing
- `POST /api/traces/simple` - Create automatic span
- `POST /api/traces/multi-step` - Create manual span with multiple steps

### Feature Flags
- `GET /api/feature-demo` - Demonstrate feature flag integration

### Health
- `GET /api/health` - Health check endpoint
- `GET /` - API information

## Viewing Observability Data

1. Log in to your LaunchDarkly account
2. Navigate to **Observability** in the left sidebar
3. You'll see:
   - **Errors**: All captured errors with stack traces, context, and timestamps
   - **Logs**: Structured logs with severity levels and metadata
   - **Traces**: Distributed traces showing request flows from frontend to backend
   - **Metrics**: Auto-generated metrics based on OpenTelemetry data

## Configuration

### Backend Configuration (`.env`)

```bash
# LaunchDarkly server-side SDK key
LD_SDK_KEY=sdk-key-123abc

# Observability settings
SERVICE_NAME=python-observability-demo
SERVICE_VERSION=1.0.0
ENVIRONMENT=development

# Flask settings
FLASK_ENV=development
FLASK_PORT=5000
```

### Frontend Configuration (`.env`)

```bash
# LaunchDarkly client-side ID (not secret)
VITE_LD_CLIENT_SIDE_ID=your-client-side-id

# Backend API URL
VITE_API_URL=http://localhost:5000
```

## Key Implementation Details

### Python SDK Initialization

```python
from ldobserve import ObservabilityConfig, ObservabilityPlugin

observability_config = ObservabilityConfig(
    service_name='python-observability-demo',
    service_version='1.0.0',
    environment='development'
)

plugin = ObservabilityPlugin(observability_config)

config = Config(
    sdk_key=sdk_key,
    plugins=[plugin]
)

ldclient.set_config(config)
```

### Error Recording

```python
import ldobserve

try:
    # Some operation
    raise ValueError("Something went wrong")
except Exception as error:
    ldobserve.record_error(
        error,
        'Operation failed',
        {'context': 'additional_info'}
    )
```

### Logging

```python
ldobserve.record_log(
    'User action completed',
    'info',
    {'user_id': 123, 'action': 'purchase'}
)
```

### Tracing

```python
# Automatic span
with ldobserve.start_span('operation.name') as span:
    span.set_attribute('key', 'value')
    # Operation here
    # Span ends automatically

# Manual span with multiple steps
with ldobserve.start_manual_span('workflow.name') as span:
    try:
        span.set_attribute('step', 1)
        # Step 1
        span.set_attribute('step', 2)
        # Step 2
        span.set_status_ok()
    except Exception as error:
        span.set_status_error(str(error))
```

### Feature Flag Evaluation

```python
flag_value = client.variation('pythonDemoFeature', context, False)

if flag_value:
    # Enhanced behavior
    return enhanced_response
else:
    # Basic behavior
    return basic_response
```

## Troubleshooting

### Backend won't start

- Ensure Python 3.10+ is installed: `python --version`
- Activate virtual environment: `source venv/bin/activate`
- Install dependencies: `pip install -r requirements.txt`
- Check `.env` file exists with valid SDK key

### Frontend can't connect to backend

- Ensure backend is running on port 5000
- Check `VITE_API_URL` in frontend `.env`
- Check browser console for CORS errors

### No data in LaunchDarkly

- Verify SDK keys are correct
- Check LaunchDarkly account has observability features enabled
- Look for errors in backend terminal output
- Ensure you're looking at the correct environment in LaunchDarkly

## Resources

- [LaunchDarkly Python SDK Observability Docs](https://launchdarkly.com/docs/sdk/observability/python)
- [LaunchDarkly Python SDK Docs](https://launchdarkly.com/docs/sdk/server-side/python)
- [LaunchDarkly Observability Overview](https://launchdarkly.com/docs/home/observability)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)

## Training Resources

This demo is designed for training on LaunchDarkly observability features. Use it to:

1. **Learn the Basics**: Understand error tracking, logging, and tracing
2. **Explore the API**: See real-world usage patterns
3. **Test Integration**: Experiment with your own modifications
4. **Practice Troubleshooting**: Use observability data to debug issues

## Support

For questions or issues:
- [LaunchDarkly Support](https://support.launchdarkly.com/)
- [LaunchDarkly Community](https://launchdarkly.com/community/)

## License

This demo application is provided as-is for educational purposes.


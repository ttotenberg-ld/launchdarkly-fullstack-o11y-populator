# Frontend & Backend Observability Implementation

This document describes the implementation of LaunchDarkly Observability for both frontend and backend with clear source attribution.

## Overview

All telemetry signals (logs, errors, and traces) now include clear **source attribution** to distinguish between frontend and backend origins:

- **Frontend signals** include: `source: 'frontend'`, `service: 'react-frontend'`
- **Backend signals** include: `source: 'backend'`, `service: 'python-backend'`

### Distributed Tracing

This demo showcases **distributed tracing** - a key observability feature that allows you to track a single request as it flows through multiple services. When you click a button in the frontend:

1. **Frontend** creates a trace span around the API call
2. **Trace context** (trace ID, span ID) is automatically propagated via HTTP headers (W3C Trace Context standard)
3. **Backend** receives the request and continues the trace by creating child spans
4. **Result**: A single cohesive trace showing the complete frontend-to-backend journey

This gives you visibility into:
- End-to-end request latency
- Where time is spent (frontend vs backend)
- How services communicate
- Error propagation across service boundaries

## Frontend Implementation (React/JavaScript)

### 1. Error Tracking (`ErrorBoundary.jsx`, `ErrorDemo.jsx`)

**ErrorBoundary Component:**
```javascript
import { LDObserve } from '@launchdarkly/observability';

componentDidCatch(error, errorInfo) {
  LDObserve.recordError(error, 'React Error Boundary caught an error', {
    source: 'frontend',
    service: 'react-frontend',
    component: 'ErrorBoundary',
    componentStack: errorInfo.componentStack
  });
}
```

**Manual Error Recording:**
```javascript
try {
  throw new Error('Something went wrong');
} catch (error) {
  LDObserve.recordError(error, 'Manual error from button click', {
    source: 'frontend',
    service: 'react-frontend',
    component: 'ErrorDemo.jsx',
    errorType: error.name || 'Error'
  });
}
```

### 2. Logging (`LogsDemo.jsx`)

```javascript
import { LDObserve } from '@launchdarkly/observability';

// Record logs with different severity levels
LDObserve.recordLog('Frontend debug log message', 'debug', {
  source: 'frontend',
  service: 'react-frontend',
  component: 'LogsDemo.jsx',
  timestamp: new Date().toISOString()
});

LDObserve.recordLog('Frontend info log message', 'info', {
  source: 'frontend',
  service: 'react-frontend',
  component: 'LogsDemo.jsx'
});
```

**Available severity levels:** `'debug'`, `'info'`, `'warn'`, `'error'`

### 3. Distributed Tracing (`TracesDemo.jsx`)

**Simple Distributed Trace (automatic span):**
```javascript
// Frontend creates a span around the API call
await LDObserve.startSpan('distributed.api.simple', async (span) => {
  span.setAttribute('source', 'frontend');
  span.setAttribute('service', 'react-frontend');
  span.setAttribute('endpoint', '/api/traces/simple');
  
  // Make API call - trace context is automatically propagated to backend
  const response = await fetch(`${API_URL}/api/traces/simple`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  });
  
  const data = await response.json();
  span.setAttribute('http.status_code', response.status);
  span.setStatus({ code: 1 }); // OK (UNSET=0, OK=1, ERROR=2)
  // Span ends automatically when callback completes
});
```

**Multi-Step Distributed Trace (manual span):**
```javascript
LDObserve.startManualSpan('distributed.workflow.multi_step', async (span) => {
  try {
    span.setAttribute('source', 'frontend');
    span.setAttribute('service', 'react-frontend');
    span.setAttribute('operation.type', 'distributed_multi_step');
    
    // Make API call to backend - backend continues the trace
    const response = await fetch(`${API_URL}/api/traces/multi-step`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    
    const data = await response.json();
    span.setAttribute('backend.completed_steps', data.completed_steps);
    span.setStatus({ code: 1 }); // OK
  } catch (error) {
    span.setStatus({ code: 2, message: error.message }); // ERROR
  } finally {
    span.end(); // MUST call this!
  }
});
```

## Backend Implementation (Python/Flask)

### 1. Error Tracking (`app.py`)

```python
from ldobserve.observe import record_exception

try:
    # Your operation here
    result = perform_operation()
except Exception as error:
    record_exception(error, {
        'source': 'backend',
        'service': 'python-backend',
        'endpoint': '/api/errors/manual',
        'demo_type': 'manual_error',
        'message': 'Operation failed'
    })
    raise
```

**Global error handler:**
```python
@app.errorhandler(Exception)
def handle_exception(error):
    record_exception(error, {
        'source': 'backend',
        'service': 'python-backend',
        'error_type': type(error).__name__,
        'message': 'Uncaught exception in Flask application'
    })
    return jsonify({'error': str(error)}), 500
```

### 2. Logging (`app.py`)

```python
from ldobserve.observe import record_log, LEVELS

record_log('Processing request', LEVELS['info'], {
    'source': 'backend',
    'service': 'python-backend',
    'endpoint': '/api/data',
    'timestamp': time.time()
})
```

**Available severity levels:** `LEVELS['debug']`, `LEVELS['info']`, `LEVELS['warning']`, `LEVELS['error']`

### 3. Tracing (`app.py`)

**Context Manager (automatic span management):**
```python
from ldobserve.observe import start_span

with start_span('backend.api.fetch.simple') as span:
    span.set_attribute('source', 'backend')
    span.set_attribute('service', 'python-backend')
    span.set_attribute('operation.type', 'simple_fetch')
    
    # Your operation here
    # Span ends automatically when context exits
```

**Multi-step workflow:**
```python
with start_span('backend.workflow.multi_step') as span:
    try:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', 'python-backend')
        span.set_attribute('workflow.total_steps', 3)
        
        # Step 1
        time.sleep(0.6)
        span.set_attribute('step.1.completed', True)
        
        # Step 2
        time.sleep(0.6)
        span.set_attribute('step.2.completed', True)
        
        # Step 3
        time.sleep(0.6)
        span.set_attribute('step.3.completed', True)
        
    except Exception as error:
        record_exception(error, {
            'source': 'backend',
            'message': 'Workflow failed'
        })
        raise
```

## Components Updated

### Frontend Components
1. **ErrorBoundary.jsx** - React Error Boundary with frontend error tracking
2. **ErrorDemo.jsx** - Frontend error demonstrations with manual and boundary-caught errors
3. **LogsDemo.jsx** - Frontend and backend logging demonstrations
4. **TracesDemo.jsx** - Distributed tracing demonstrations showing frontend-to-backend request flows

### Backend Files
1. **app.py** - All endpoints updated with consistent source attribution:
   - Error endpoints (`/api/errors/*`)
   - Logging endpoints (`/api/logs/*`)
   - Tracing endpoints (`/api/traces/*`)

## Benefits of Distributed Tracing with Source Attribution

1. **Complete Request Visibility**: See the entire request journey from frontend through backend in a single trace
2. **Performance Insights**: Understand where time is spent - is the frontend slow or is the backend taking too long?
3. **Easy Filtering**: Filter telemetry by `source: 'frontend'` or `source: 'backend'` in LaunchDarkly dashboard
4. **Service Identification**: Additional `service` attribute for more granular filtering
5. **Error Correlation**: When an error occurs, see which service caused it and how it propagated
6. **Clear Ownership**: Immediately identify whether an issue originates from frontend or backend
7. **Component Tracking**: Frontend includes `component` attribute for specific file identification

## Testing the Implementation

### Frontend Errors
1. Click "Frontend: Manual Error" - Records a manually caught error
2. Click "Frontend: React Error Boundary" - Triggers React Error Boundary
3. Click "Both: Frontend + Backend" - Demonstrates both sources

### Frontend Logs
1. Click any "Frontend: *" log button - Records frontend log
2. Click any "Backend: *" log button - Calls backend endpoint

### Distributed Traces
1. Click "Run Simple Distributed Trace" - Creates a trace that spans from frontend through backend
2. Click "Run Multi-Step Distributed Trace" - Creates a distributed trace with backend multi-step processing

## Configuration

### Frontend
- SDK initialized in `main.jsx` with `@launchdarkly/observability` plugin
- Environment variable: `VITE_LD_CLIENT_SIDE_ID`
- CSP headers in `index.html` for LaunchDarkly domains

### Backend
- SDK initialized in `app.py` with `ObservabilityPlugin`
- Environment variables:
  - `LD_SDK_KEY`
  - `SERVICE_NAME` (default: 'python-observability-demo')
  - `SERVICE_VERSION` (default: '1.0.0')
  - `ENVIRONMENT` (default: 'development')

## Best Practices

1. **Always include source attribution**: Every telemetry signal should have `source` and `service` attributes
2. **Use descriptive span names**: Prefix with `distributed.*` for frontend-to-backend traces, `backend.*` for backend-only operations
3. **Wrap API calls in spans**: Create a span around your API calls in the frontend to enable distributed tracing
4. **Add context**: Include relevant metadata like component names, endpoints, timestamps, HTTP status codes
5. **Handle errors gracefully**: Always record errors before re-throwing
6. **End manual spans**: Always call `span.end()` in a finally block for manual spans
7. **Let trace context propagate automatically**: Don't manually pass trace IDs - the SDKs handle this via HTTP headers

## Naming Conventions

### Distributed Trace Spans
- `distributed.api.*` - Distributed API calls from frontend through backend
- `distributed.workflow.*` - Multi-step distributed workflows
- `backend.api.fetch.*` - Backend-only API fetch operations
- `backend.workflow.*` - Backend-only multi-step workflows
- `backend.operation.*` - Generic backend operations

**Best Practice:** Use `distributed.*` prefix for spans that start in the frontend and involve backend calls. This makes it clear that the trace spans multiple services.

## Troubleshooting

1. **No telemetry data**: Check that both frontend and backend SDK keys are configured
2. **Missing source attribution**: Verify all `recordError`, `recordLog`, and `startSpan` calls include source attributes
3. **Traces not connected**: If frontend and backend traces appear as separate traces, verify that:
   - Frontend creates a span AROUND the fetch call (not before or after)
   - Backend SDK is properly initialized with observability plugin
   - Trace context propagation is enabled (automatic in LaunchDarkly SDKs)
4. **CSP violations**: Ensure `index.html` includes all required LaunchDarkly domains in CSP headers
5. **Backend not running**: Frontend shows alerts when backend API calls fail


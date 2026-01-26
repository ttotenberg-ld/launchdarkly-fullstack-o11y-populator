# Testing Guide - Frontend & Backend Observability

This guide will help you test the frontend and backend observability implementation with clear source attribution.

## Prerequisites

1. **Backend Running**: Start the Python Flask backend
   ```bash
   cd backend
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   python app.py
   ```
   Backend should be running on `http://localhost:5001`

2. **Frontend Running**: Start the React frontend
   ```bash
   cd frontend
   npm run dev
   ```
   Frontend should be running on `http://localhost:5173`

3. **LaunchDarkly Dashboard**: Open your LaunchDarkly dashboard at https://app.launchdarkly.com and navigate to the **Monitor** section

## Testing Error Tracking

### Backend Errors
1. Click **"Backend: Manual Error"**
   - ✅ Should show success alert
   - 📊 Check dashboard: Look for error with `source: 'backend'`, `service: 'python-backend'`
   - 🏷️ Tags: `endpoint: '/api/errors/manual'`, `demo_type: 'manual_error'`

2. Click **"Backend: Async Error"**
   - ✅ Should show success alert after 1 second delay
   - 📊 Check dashboard: Look for error with `source: 'backend'`, `delay_seconds: 1`

3. Click **"Backend: Uncaught Error"**
   - ✅ Should show success alert
   - 📊 Check dashboard: Look for error with `demo_type: 'uncaught_error'`

### Frontend Errors
4. Click **"Frontend: Manual Error"**
   - ✅ Should show browser alert
   - 📊 Check dashboard: Look for error with `source: 'frontend'`, `service: 'react-frontend'`
   - 🏷️ Tags: `component: 'ErrorDemo.jsx'`, `demo_type: 'manual_frontend_error'`

5. Click **"Frontend: React Error Boundary"**
   - ✅ Should show error boundary fallback UI
   - 📊 Check dashboard: Look for error with `source: 'frontend'`, `component: 'ErrorBoundary'`
   - 🔄 Click "Reset and Try Again" to return to normal UI

### Combined Test
6. Click **"🚨 Both: Frontend + Backend"**
   - ✅ Should show backend success, then error boundary
   - 📊 Check dashboard: Should see TWO errors:
     - One with `source: 'backend'`
     - One with `source: 'frontend'`, `triggered_after_backend: true`

## Testing Logs

### Frontend Logs
1. Click **"Frontend: Debug Log"**
   - 📊 Check dashboard: Log with `source: 'frontend'`, severity: `debug`

2. Click **"Frontend: Info Log"**
   - 📊 Check dashboard: Log with `source: 'frontend'`, severity: `info`

3. Click **"Frontend: Warning Log"**
   - 📊 Check dashboard: Log with `source: 'frontend'`, severity: `warn`

4. Click **"Frontend: Error Log"**
   - 📊 Check dashboard: Log with `source: 'frontend'`, severity: `error`

### Backend Logs
5. Click **"Backend: Debug Log"**
   - 📊 Check dashboard: Log with `source: 'backend'`, `endpoint: '/api/logs/debug'`

6. Click **"Backend: Info Log"**
   - 📊 Check dashboard: Log with `source: 'backend'`, `endpoint: '/api/logs/info'`

7. Click **"Backend: Warning Log"**
   - 📊 Check dashboard: Log with `source: 'backend'`, `endpoint: '/api/logs/warn'`

8. Click **"Backend: Error Log"**
   - 📊 Check dashboard: Log with `source: 'backend'`, `endpoint: '/api/logs/error'`

## Testing Traces

### Frontend Traces

#### Automatic Span
1. Click **"Frontend: Run Simple Operation"**
   - ✅ Wait ~800ms
   - ✅ Should see success message: "✓ Frontend: Fetched ..."
   - 📊 Check dashboard: Trace span named `frontend.api.fetch.simple`
   - 🏷️ Tags: `source: 'frontend'`, `service: 'react-frontend'`, `operation.type: 'simple_fetch'`

#### Manual Span
2. Click **"Frontend: Run Multi-Step Workflow"**
   - ✅ Watch progress messages update (Step 1/3, 2/3, 3/3)
   - ✅ Should see success message: "✓ Frontend: Completed 3/3 steps!"
   - 📊 Check dashboard: Trace span named `frontend.workflow.multi_step`
   - 🏷️ Tags: `source: 'frontend'`, `step.1.completed: true`, `step.2.completed: true`, `step.3.completed: true`

### Backend Traces

#### Automatic Span
3. Click **"Backend: Run Simple API Fetch"**
   - ✅ Wait ~800ms
   - ✅ Should see success message: "✓ Backend: Fetched ..."
   - 📊 Check dashboard: Trace span named `backend.api.fetch.simple`
   - 🏷️ Tags: `source: 'backend'`, `service: 'python-backend'`, `operation.type: 'simple_fetch'`

#### Manual Span
4. Click **"Backend: Run Multi-Step Workflow"**
   - ✅ Wait ~2 seconds
   - ✅ Should see success message: "✓ Backend: Completed 3/3 steps!"
   - 📊 Check dashboard: Trace span named `backend.workflow.multi_step`
   - 🏷️ Tags: `source: 'backend'`, `step.1.completed: true`, `step.2.completed: true`, `step.3.completed: true`

## Filtering in LaunchDarkly Dashboard

### Filter by Source
- **Frontend only**: Filter by `source: 'frontend'` or `service: 'react-frontend'`
- **Backend only**: Filter by `source: 'backend'` or `service: 'python-backend'`

### Filter by Component (Frontend)
- Filter by `component: 'ErrorDemo.jsx'` to see only errors from that component
- Filter by `component: 'ErrorBoundary'` to see boundary-caught errors

### Filter by Endpoint (Backend)
- Filter by `endpoint: '/api/errors/manual'` to see errors from that endpoint
- Filter by `endpoint: '/api/logs/debug'` to see logs from that endpoint

## Expected Results Summary

| Test Type | Frontend Count | Backend Count | Total |
|-----------|----------------|---------------|-------|
| Errors | 3 individual + 1 in combined test | 3 individual + 1 in combined test | 8 |
| Logs | 4 severity levels | 4 severity levels | 8 |
| Traces | 2 patterns (auto + manual) | 2 patterns (auto + manual) | 4 |

## Troubleshooting

### No Data Appearing in Dashboard
1. ✅ Check that `VITE_LD_CLIENT_SIDE_ID` is set in frontend `.env`
2. ✅ Check that `LD_SDK_KEY` is set in backend `.env`
3. ✅ Verify both frontend and backend are running
4. ✅ Check browser console for errors
5. ✅ Wait a few seconds - telemetry may be batched

### Backend Connection Failed
1. ✅ Ensure backend is running on correct port (default: 5001)
2. ✅ Check `VITE_API_URL` in frontend `.env` matches backend port
3. ✅ Verify CORS is enabled in backend (already configured)

### Error Boundary Not Resetting
1. Click "Reset and Try Again" button
2. If that doesn't work, refresh the page

### Missing Source Attribution
1. Check that you're using the latest code
2. Verify all telemetry includes `source` and `service` attributes
3. Look for the attributes in the dashboard's event details

## Key Attributes to Look For

### All Telemetry Should Have:
- ✅ `source`: Either `'frontend'` or `'backend'`
- ✅ `service`: Either `'react-frontend'` or `'python-backend'`

### Frontend Should Also Have:
- ✅ `component`: The React component name (e.g., `'ErrorDemo.jsx'`)

### Backend Should Also Have:
- ✅ `endpoint`: The API endpoint (e.g., `'/api/errors/manual'`)

## Next Steps

1. ✅ Test all error, log, and trace scenarios
2. ✅ Verify source attribution in LaunchDarkly dashboard
3. ✅ Experiment with filtering by source, service, component, and endpoint
4. ✅ Try creating your own custom telemetry following the patterns
5. ✅ Review `OBSERVABILITY_IMPLEMENTATION.md` for API details

## Questions?

Refer to:
- `OBSERVABILITY_IMPLEMENTATION.md` - Full API documentation
- `example/` directory - Reference implementation
- LaunchDarkly documentation - https://docs.launchdarkly.com


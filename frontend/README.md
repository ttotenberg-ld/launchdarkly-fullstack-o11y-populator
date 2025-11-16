# LaunchDarkly Python Observability - Frontend

React frontend for the LaunchDarkly Python observability demo. This application provides an interactive interface to trigger observability events on the Python backend.

## Overview

The frontend demonstrates distributed tracing by making HTTP requests to the Python Flask backend. Each button click triggers a backend API call that generates observability data (errors, logs, or traces) which is then sent to LaunchDarkly.

## Features

- **Error Demo**: Trigger different types of errors on the backend
- **Logs Demo**: Generate logs at various severity levels
- **Traces Demo**: Create distributed traces from frontend to backend
- **Real-time Feedback**: See immediate results from backend API calls
- **LaunchDarkly Integration**: Client-side SDK for frontend observability (optional)

## Prerequisites

- Node.js 16+ and npm
- Backend server running on http://localhost:5000
- LaunchDarkly client-side ID

## Installation

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env`:

```bash
# LaunchDarkly Client-Side ID (not secret, safe for frontend)
# Get from: LaunchDarkly Dashboard > Project Settings > Environments > Client-side ID
VITE_LD_CLIENT_SIDE_ID=your-client-side-id

# Backend API URL
VITE_API_URL=http://localhost:5000
```

## Running the Application

### Development Mode

```bash
npm run dev
```

Application will start on http://localhost:5173 (or next available port).

### Build for Production

```bash
npm run build
```

### Preview Production Build

```bash
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── DashboardLayout.jsx    # Main layout container
│   │   ├── ErrorBoundary.jsx      # Error boundary wrapper
│   │   ├── ErrorDemo.jsx          # Error tracking UI
│   │   ├── LogsDemo.jsx           # Logging UI
│   │   ├── TracesDemo.jsx         # Distributed tracing UI
│   │   └── FancyWidget.jsx        # Feature flag demo
│   ├── App.jsx                    # Root component
│   ├── main.jsx                   # Entry point with LD initialization
│   └── index.css                  # Global styles
├── public/                        # Static assets
├── index.html                     # HTML template
├── vite.config.js                 # Vite configuration
├── package.json                   # Dependencies
└── .env                           # Environment config (gitignored)
```

## Component Overview

### ErrorDemo.jsx

Triggers error endpoints on the Python backend:

- **Manual Error**: Calls `/api/errors/manual`
- **Async Error**: Calls `/api/errors/async` (with 1s delay)
- **Uncaught Error**: Calls `/api/errors/uncaught`

All errors are recorded on the backend and sent to LaunchDarkly.

### LogsDemo.jsx

Triggers logging endpoints on the Python backend:

- **Debug Log**: Calls `/api/logs/debug`
- **Info Log**: Calls `/api/logs/info`
- **Warning Log**: Calls `/api/logs/warn`
- **Error Log**: Calls `/api/logs/error`

Logs are recorded on the backend with appropriate severity levels.

### TracesDemo.jsx

Triggers tracing endpoints on the Python backend:

- **Simple Trace**: Calls `/api/traces/simple` (automatic span)
- **Multi-Step Trace**: Calls `/api/traces/multi-step` (manual span with 3 steps)

Demonstrates distributed tracing from frontend HTTP request to backend processing.

## API Integration

All components use the same pattern to call the backend:

```javascript
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

const handleAction = async () => {
  try {
    const response = await fetch(`${API_URL}/api/endpoint`);
    const data = await response.json();
    // Handle success
  } catch (error) {
    console.error('Failed to call backend:', error);
    alert('Failed to call backend API. Make sure the backend server is running.');
  }
};
```

## Environment Variables

### `VITE_LD_CLIENT_SIDE_ID`

LaunchDarkly client-side ID for frontend SDK initialization.

- **Required**: Yes (for LaunchDarkly features)
- **Secret**: No (safe to include in frontend code)
- **Get From**: LaunchDarkly Dashboard → Project Settings → Environments

### `VITE_API_URL`

URL of the Python Flask backend API.

- **Required**: Yes
- **Default**: `http://localhost:5000`
- **Production**: Update to your deployed backend URL

## LaunchDarkly Client-Side SDK

The frontend includes LaunchDarkly's React SDK for:

- Feature flag evaluation
- Real-time flag updates
- Client-side observability (optional)

### Initialization

In `main.jsx`:

```javascript
import { asyncWithLDProvider } from 'launchdarkly-react-client-sdk';

const LDProvider = await asyncWithLDProvider({
  clientSideID: import.meta.env.VITE_LD_CLIENT_SIDE_ID,
  context: {
    kind: 'user',
    key: 'demo-user',
    name: 'Demo User'
  },
  options: {
    // Client-side observability can be added here
  }
});
```

### Using Feature Flags

```javascript
import { useFlags } from 'launchdarkly-react-client-sdk';

function MyComponent() {
  const flags = useFlags();
  
  return (
    <div>
      {flags.myFeature && <NewFeature />}
    </div>
  );
}
```

## Distributed Tracing

The frontend-to-backend flow demonstrates distributed tracing:

1. **Frontend**: User clicks button
2. **HTTP Request**: Frontend sends request to backend
3. **Backend**: Python backend processes request
4. **Trace Creation**: Backend creates span with attributes
5. **LaunchDarkly**: Trace data sent to observability platform

You can see the complete trace in LaunchDarkly's Observability dashboard, showing:
- Request origin (frontend)
- Backend processing time
- Span attributes
- Any errors or logs

## Development

### Adding New Demo Components

1. Create new component in `src/components/`
2. Import and add to `DashboardLayout.jsx`
3. Follow existing patterns for API calls
4. Update documentation

### Styling

Uses inline styles for simplicity. Key patterns:

- Cards: White background, rounded corners, shadow
- Buttons: Colored backgrounds, hover effects
- Success/Error states: Green/Red color coding

### Error Handling

All API calls include try/catch blocks:

```javascript
try {
  const response = await fetch(url);
  const data = await response.json();
  // Success handling
} catch (error) {
  console.error('Error:', error);
  alert('Operation failed. Check console.');
}
```

## Troubleshooting

### Backend Connection Failed

**Symptom**: "Failed to call backend API" alerts

**Solutions**:
1. Ensure backend is running: http://localhost:5000/api/health
2. Check `VITE_API_URL` in `.env`
3. Look for CORS errors in browser console
4. Verify backend CORS is configured correctly

### LaunchDarkly SDK Not Initializing

**Symptom**: Feature flags not working

**Solutions**:
1. Verify `VITE_LD_CLIENT_SIDE_ID` is set correctly
2. Check browser console for SDK errors
3. Ensure client-side ID (not SDK key) is used
4. Check network tab for LaunchDarkly API calls

### Build Errors

**Symptom**: `npm run build` fails

**Solutions**:
1. Delete `node_modules` and run `npm install`
2. Check Node.js version: `node --version` (should be 16+)
3. Clear Vite cache: `rm -rf node_modules/.vite`

### Hot Reload Not Working

**Symptom**: Changes not reflected in browser

**Solutions**:
1. Restart dev server: Stop and run `npm run dev` again
2. Hard refresh browser: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)
3. Check for console errors

## Code Examples

### Calling Error Endpoint

```javascript
const handleManualError = async () => {
  try {
    const response = await fetch(`${API_URL}/api/errors/manual`);
    const data = await response.json();
    console.log('Error recorded:', data);
    alert(`Error recorded: ${data.error_message}`);
  } catch (error) {
    console.error('Failed:', error);
  }
};
```

### Calling Trace Endpoint

```javascript
const handleTrace = async () => {
  try {
    const response = await fetch(`${API_URL}/api/traces/simple`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    const data = await response.json();
    console.log('Trace created:', data);
  } catch (error) {
    console.error('Failed:', error);
  }
};
```

## Dependencies

### Core Dependencies

- `react` (^18.3.1) - UI library
- `react-dom` (^18.3.1) - React DOM renderer
- `launchdarkly-react-client-sdk` (^3.0.0) - LaunchDarkly React SDK
- `launchdarkly-js-client-sdk` (^3.7.0) - LaunchDarkly JS SDK
- `@launchdarkly/observability` (^0.4.7) - Observability plugin (optional)
- `@launchdarkly/session-replay` (^0.4.0) - Session replay (optional)

### Dev Dependencies

- `vite` (^6.0.1) - Build tool
- `@vitejs/plugin-react` (^4.3.4) - React plugin for Vite

## Best Practices

1. **Always check backend status** before making requests
2. **Provide clear user feedback** for all actions
3. **Handle errors gracefully** with user-friendly messages
4. **Use environment variables** for configuration
5. **Include loading states** for async operations
6. **Log errors to console** for debugging

## Architecture Notes

### Why Frontend + Backend?

This architecture demonstrates:
- **Distributed Tracing**: See request flow across services
- **Realistic Patterns**: How real applications integrate observability
- **Backend Focus**: Python observability is the primary focus
- **Frontend Simplicity**: React provides clean, interactive UI

### Alternative: Backend Only

You could simplify by removing React and using:
- Plain HTML with vanilla JavaScript
- Flask templates with Jinja2
- Command-line scripts

The current setup provides the best balance of realism and usability for training.

## Resources

- [LaunchDarkly React SDK Docs](https://docs.launchdarkly.com/sdk/client-side/react/react-web)
- [Vite Documentation](https://vitejs.dev/)
- [React Documentation](https://react.dev/)

## Support

For issues or questions:
- [LaunchDarkly Support](https://support.launchdarkly.com/)
- [LaunchDarkly Community](https://launchdarkly.com/community/)


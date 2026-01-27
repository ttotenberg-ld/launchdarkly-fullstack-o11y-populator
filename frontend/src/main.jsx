import React from 'react'
import ReactDOM from 'react-dom/client'
import { asyncWithLDProvider } from 'launchdarkly-react-client-sdk'
import Observability from '@launchdarkly/observability'
import SessionReplay from '@launchdarkly/session-replay'
import App from './App.jsx'
import './index.css'
import { initializeErrorInjection } from './utils/errorInjection'

// Build tracingOrigins patterns for distributed tracing
// This determines which outgoing requests get trace context headers added
const apiUrl = import.meta.env.VITE_API_URL || '';
const tracingOrigins = [
  /localhost:5000/,           // Local development - direct API access
  /localhost:3000/,           // Local development - via frontend proxy
  /api-gateway/,              // Docker internal network
  /127\.0\.0\.1/,             // Local IP
];

// Add the current origin (critical for same-origin API requests via nginx proxy)
try {
  const currentOrigin = window.location.origin;
  const escapedOrigin = currentOrigin.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  tracingOrigins.push(new RegExp(escapedOrigin));
} catch {
  // Window not available (SSR), skip
}

// Add the configured API URL as a pattern if specified
if (apiUrl) {
  try {
    const url = new URL(apiUrl);
    const escapedHost = url.host.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    tracingOrigins.push(new RegExp(escapedHost));
  } catch {
    // If not a valid URL, add as-is
    tracingOrigins.push(new RegExp(apiUrl.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  }
}

(async () => {
  try {
    const clientSideID = import.meta.env.VITE_LD_CLIENT_SIDE_ID;
    
    if (!clientSideID) {
      throw new Error('LaunchDarkly client-side ID not found in environment variables. Please set VITE_LD_CLIENT_SIDE_ID in your .env file.');
    }

    const LDProvider = await asyncWithLDProvider({
      clientSideID,
      context: {
        kind: 'user',
        key: 'anonymous-' + Math.random().toString(36).substr(2, 9),
        anonymous: true
      },
      options: {
        plugins: [
          new Observability({
            version: '1.0.0',
            tracingOrigins: tracingOrigins,
            networkRecording: {
              enabled: true,
              recordHeadersAndBody: true
            }
          }),
          new SessionReplay({
            privacySetting: 'none',
            inlineStylesheet: true
          })
        ]
      }
    });

    // Initialize error injection for observability demo
    // This may inject random errors to simulate real-world error scenarios
    // Errors are captured by the Observability SDK and will appear on documentLoad spans
    initializeErrorInjection();

    ReactDOM.createRoot(document.getElementById('root')).render(
      <React.StrictMode>
        <LDProvider>
          <App />
        </LDProvider>
      </React.StrictMode>,
    );
  } catch (err) {
    console.error('Failed to initialize LaunchDarkly:', err);
    
    // Render error message if initialization fails
    ReactDOM.createRoot(document.getElementById('root')).render(
      <React.StrictMode>
        <div style={{ 
          display: 'flex', 
          justifyContent: 'center', 
          alignItems: 'center', 
          height: '100vh',
          flexDirection: 'column',
          color: 'white',
          padding: '20px',
          textAlign: 'center'
        }}>
          <h1>Initialization Error</h1>
          <p style={{ marginTop: '10px' }}>{err.message}</p>
        </div>
      </React.StrictMode>,
    );
  }
})();


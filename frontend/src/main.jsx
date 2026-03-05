import React from 'react'
import ReactDOM from 'react-dom/client'
import { asyncWithLDProvider } from 'launchdarkly-react-client-sdk'
import Observability from '@launchdarkly/observability'
import SessionReplay from '@launchdarkly/session-replay'
import App from './App.jsx'
import './index.css'
import {
  initializeErrorInjection,
  setupDocumentLoadErrors,
  registerDocumentLoadErrorProcessor,
} from './utils/errorInjection'

(async () => {
  // Register documentLoad error handler BEFORE SDK initialization.
  // Fallback mechanism: throws errors during the 'load' event. The SDK's
  // window.onerror creates highlight.exception spans with timestamps that
  // overlap the documentLoad time window (server-side time correlation).
  setupDocumentLoadErrors();

  try {
    const clientSideID = import.meta.env.VITE_LD_CLIENT_SIDE_ID;

    if (!clientSideID) {
      throw new Error('LaunchDarkly client-side ID not found in environment variables. Please set VITE_LD_CLIENT_SIDE_ID in your .env file.');
    }

    // Start SDK initialization — this SYNCHRONOUSLY creates the OTel
    // TracerProvider and registers it globally, but the returned Promise
    // doesn't resolve until the LD client receives flag data via streaming.
    const providerPromise = asyncWithLDProvider({
      clientSideID,
      context: {
        kind: 'user',
        key: Math.random().toString(36).substr(2, 9)
      },
      options: {
        plugins: [
          new Observability({
            version: '1.0.0',
            tracingOrigins: true,
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

    // PRIMARY: Register a custom OTel SpanProcessor that injects errors
    // directly onto documentLoad spans when they're created. This must happen
    // AFTER asyncWithLDProvider() is called (TracerProvider exists) but BEFORE
    // the 'load' event fires (which triggers documentLoad span creation via
    // a deferred setTimeout inside the SDK's _onDocumentLoaded).
    registerDocumentLoadErrorProcessor();

    // Wait for the LD client to receive flag data
    const LDProvider = await providerPromise;

    // Initialize post-load error injection after SDK is ready.
    // These create session-level errors via LDObserve.recordError().
    // (documentLoad errors are handled by the SpanProcessor above)
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

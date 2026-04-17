import React from 'react'
import ReactDOM from 'react-dom/client'
import { asyncWithLDProvider } from 'launchdarkly-react-client-sdk'
import Observability from '@launchdarkly/observability'
import SessionReplay from '@launchdarkly/session-replay'
import App from './App.jsx'
import './index.css'

(async () => {
  try {
    const clientSideID = import.meta.env.VITE_LD_CLIENT_SIDE_ID;

    if (!clientSideID) {
      throw new Error('LaunchDarkly client-side ID not found in environment variables. Please set VITE_LD_CLIENT_SIDE_ID in your .env file.');
    }

    // Use injected user identity from simulator if available, otherwise
    // generate a random key for local dev. This keeps the LD client-side
    // context aligned with the X-User-* headers sent on API requests.
    const ldUser = typeof window !== 'undefined' ? window.__LD_USER__ : null;
    const userKey = ldUser?.key || Math.random().toString(36).substr(2, 9);

    // Browser profile injected by the simulator (e.g. 'mobile_ios_safari',
    // 'desktop_firefox'). Undefined for real human traffic; that's fine —
    // the attribute just won't exist on those contexts and LD targeting
    // clauses that reference it simply won't match. formFactor is a
    // coarser split for the common "mobile vs desktop" targeting case.
    const browserProfile = typeof window !== 'undefined' ? window.__BROWSER_PROFILE__ : null;
    const formFactor = browserProfile?.startsWith('mobile_')
      ? 'mobile'
      : browserProfile?.startsWith('desktop_')
        ? 'desktop'
        : null;

    // Fetch the session replay privacy flag BEFORE SDK init, because
    // SessionReplay's privacySetting can only be set in the constructor.
    // Uses LD's client-side eval endpoint (no SDK needed).
    let privacySetting = 'none'; // fallback if fetch fails
    try {
      const evalResp = await fetch(
        `https://clientsdk.launchdarkly.com/sdk/evalx/${clientSideID}/contexts/${btoa(JSON.stringify({ kind: 'user', key: userKey }))}`,
        { headers: { 'Content-Type': 'application/json' }, signal: AbortSignal.timeout(2000) }
      );
      if (evalResp.ok) {
        const flags = await evalResp.json();
        const flagData = flags['session-replay-privacy'];
        if (flagData && ['none', 'default', 'strict'].includes(flagData.value)) {
          privacySetting = flagData.value;
        }
      }
    } catch (e) {
      console.warn('Failed to fetch session-replay-privacy flag, using default:', e);
    }

    // Start SDK initialization — this SYNCHRONOUSLY creates the OTel
    // TracerProvider and registers it globally, but the returned Promise
    // doesn't resolve until the LD client receives flag data via streaming.
    const providerPromise = asyncWithLDProvider({
      clientSideID,
      context: {
        kind: 'user',
        key: userKey,
        ...(ldUser && {
          name: ldUser.name,
          email: ldUser.email,
          plan: ldUser.plan,
          role: ldUser.role,
          metro: ldUser.metro,
          country: ldUser.country,
        }),
        // Simulator-only: fold browser profile into the INITIAL context
        // so the first flag evaluation already carries it — avoids the
        // extra round-trip a post-init identify() would cost.
        ...(browserProfile && { browserProfile, formFactor }),
      },
      options: {
        sendEventsOnlyForVariation: false,
        plugins: [
          new Observability({
            // Baked in at build time from VITE_SERVICE_VERSION (see .env /
            // docker-compose.yml). Falls back to 'dev' for local `vite dev`
            // runs without docker-compose.
            version: import.meta.env.VITE_SERVICE_VERSION || 'dev',
            tracingOrigins: true,
            networkRecording: {
              enabled: true,
              recordHeadersAndBody: true
            }
          }),
          new SessionReplay({
            privacySetting,
            inlineStylesheet: true
          })
        ]
      }
    });

    // Wait for the LD client to receive flag data
    const LDProvider = await providerPromise;

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

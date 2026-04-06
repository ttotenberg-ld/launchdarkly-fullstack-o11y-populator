import { useEffect } from 'react';
import { useLDClient } from 'launchdarkly-react-client-sdk';
import ErrorBoundary from './components/infrastructure/ErrorBoundary';
import { CartProvider } from './context/CartContext';
import { AuthProvider } from './context/AuthContext';
import Router from './Router';

// All flag keys in the tt-qr-demo project.
// Explicit variation() calls generate individual "feature" events
// (when trackEvents is enabled on the flag), which link flag evaluations
// to sessions in the LD dashboard.
const FLAG_KEYS = [
  { key: 'releaseNewUI',          defaultValue: false },
  { key: 'showChatbot',           defaultValue: false },
  { key: 'showNewFooter',         defaultValue: false },
  { key: 'showNewFeatures',       defaultValue: false },
  { key: 'showNewHero',           defaultValue: false },
  { key: 'migrate-warehouse-api', defaultValue: 'v1' },
  { key: 'product-card-layout',   defaultValue: 'standard' },
  { key: 'promo-banner',          defaultValue: 'none' },
];

function App() {
  const ldClient = useLDClient();

  // Evaluate every flag explicitly on mount so individual "feature"
  // events are generated and flushed.  This ensures the LD dashboard
  // can correlate flag evaluations with session replay data.
  useEffect(() => {
    if (ldClient) {
      FLAG_KEYS.forEach(({ key, defaultValue }) => {
        ldClient.variation(key, defaultValue);
      });

      // Flush immediately so events aren't lost if the page navigates
      // before the SDK's automatic flush interval fires.
      ldClient.flush();
    }
  }, [ldClient]);

  return (
    <ErrorBoundary>
      <AuthProvider>
        <CartProvider>
          <Router />
        </CartProvider>
      </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;


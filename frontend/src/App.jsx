import { useEffect } from 'react';
import { useLDClient } from 'launchdarkly-react-client-sdk';
import ErrorBoundary from './components/infrastructure/ErrorBoundary';
import { CartProvider } from './context/CartContext';
import { AuthProvider } from './context/AuthContext';
import Router from './Router';

function App() {
  const ldClient = useLDClient();

  // Evaluate all flags early in the user flow so analytics events are
  // sent for every flag (requires sendEventsOnlyForVariation: false).
  useEffect(() => {
    if (ldClient) {
      ldClient.allFlags();
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


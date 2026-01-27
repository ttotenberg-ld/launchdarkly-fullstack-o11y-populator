import ErrorBoundary from './components/infrastructure/ErrorBoundary';
import ErrorInjector from './components/infrastructure/ErrorInjector';
import { CartProvider } from './context/CartContext';
import { AuthProvider } from './context/AuthContext';
import Router from './Router';

function App() {
  return (
    <ErrorBoundary>
      {/* ErrorInjector may throw random errors for observability demo */}
      <ErrorInjector />
      <AuthProvider>
        <CartProvider>
          <Router />
        </CartProvider>
      </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;


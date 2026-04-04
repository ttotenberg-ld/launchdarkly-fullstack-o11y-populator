import { createBrowserRouter, RouterProvider, useRouteError } from 'react-router-dom';
import { useEffect } from 'react';
import { LDObserve } from '@launchdarkly/observability';
import Layout from './components/layout/Layout';
import Home from './pages/Home';
import Products from './pages/Products';
import ProductDetail from './pages/ProductDetail';
import Cart from './pages/Cart';
import Checkout from './pages/Checkout';
import Login from './pages/Login';
import Account from './pages/Account';
import Settings from './pages/Settings';
import OrderConfirmation from './pages/OrderConfirmation';

/**
 * Route error element that reports navigation errors (404s, etc.) to
 * LaunchDarkly Observability.  React Router v6's createBrowserRouter
 * handles route errors internally and does NOT bubble them through
 * React ErrorBoundary, so we need this dedicated errorElement.
 */
function RouteErrorBoundary() {
  const error = useRouteError();

  useEffect(() => {
    const errorObj = error instanceof Error ? error : new Error(String(error?.statusText || error?.message || error));
    console.error('Route error caught:', errorObj);

    LDObserve.recordError(
      errorObj,
      'Frontend: Route navigation error',
      {
        source: 'frontend',
        service: 'react-frontend',
        component: 'RouteErrorBoundary',
        errorType: 'NavigationError',
        status: error?.status || 'unknown',
        pathname: window.location.pathname,
      }
    );
  }, [error]);

  return (
    <div style={{
      padding: '40px',
      maxWidth: '800px',
      margin: '0 auto',
      textAlign: 'center',
    }}>
      <div className="card" style={{
        backgroundColor: '#fff3cd',
        borderLeft: '4px solid #ffc107',
      }}>
        <h1 style={{ color: '#856404', marginBottom: '20px' }}>
          ⚠️ Page Not Found
        </h1>
        <p style={{ color: '#856404', fontSize: '16px', marginBottom: '20px' }}>
          The page <code>{window.location.pathname}</code> does not exist.
          This error has been reported to LaunchDarkly Observability.
        </p>
        <button
          onClick={() => window.location.href = '/'}
          style={{
            backgroundColor: '#ffc107',
            color: '#856404',
            fontWeight: 'bold',
          }}
        >
          Go Home
        </button>
      </div>
    </div>
  );
}

const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    errorElement: <RouteErrorBoundary />,
    children: [
      {
        index: true,
        element: <Home />,
      },
      {
        path: 'products',
        element: <Products />,
      },
      {
        path: 'products/:id',
        element: <ProductDetail />,
      },
      {
        path: 'cart',
        element: <Cart />,
      },
      {
        path: 'checkout',
        element: <Checkout />,
      },
      {
        path: 'order-confirmation',
        element: <OrderConfirmation />,
      },
      {
        path: 'login',
        element: <Login />,
      },
      {
        path: 'account',
        element: <Account />,
      },
      {
        path: 'account/settings',
        element: <Settings />,
      },
    ],
  },
]);

export default function Router() {
  return <RouterProvider router={router} />;
}

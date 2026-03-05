/**
 * ErrorInjector - A component that may inject errors during React's render cycle.
 *
 * Render-phase errors are thrown and caught by the ErrorBoundary, which calls
 * LDObserve.recordError(). Async errors are recorded directly via LDObserve.recordError()
 * to match the reference implementation's pattern.
 */

import { useEffect, useRef } from 'react';
import { LDObserve } from '@launchdarkly/observability';

// Configuration
const ERROR_INJECTION_RATE = parseFloat(import.meta.env.VITE_ERROR_INJECTION_RATE || '0.05');
const ERROR_INJECTION_ENABLED = import.meta.env.VITE_ERROR_INJECTION_ENABLED !== 'false';

// Error types with realistic messages
const RENDER_ERRORS = [
  () => new TypeError("Cannot read properties of undefined (reading 'id')"),
  () => new TypeError("Cannot read properties of null (reading 'name')"),
  () => new ReferenceError('userData is not defined'),
  () => new RangeError('Invalid array length'),
  () => {
    const err = new Error('Failed to load component');
    err.name = 'ComponentLoadError';
    return err;
  },
];

// Session-level flag - determined once per page load
let sessionWillHaveRenderError = null;

function shouldInjectRenderError() {
  if (sessionWillHaveRenderError === null) {
    // Only inject render errors in ~50% of error sessions
    // (the other 50% get load errors from the main.jsx initialization)
    sessionWillHaveRenderError =
      ERROR_INJECTION_ENABLED &&
      Math.random() < ERROR_INJECTION_RATE * 0.5;
  }
  return sessionWillHaveRenderError;
}

/**
 * ErrorInjector component - renders nothing but may throw during mount.
 */
export default function ErrorInjector() {
  const hasInjected = useRef(false);

  // Only check on first mount — throw during render so ErrorBoundary catches it
  // and calls LDObserve.recordError() in componentDidCatch
  if (!hasInjected.current && shouldInjectRenderError()) {
    hasInjected.current = true;

    // Pick a random error
    const errorCreator = RENDER_ERRORS[Math.floor(Math.random() * RENDER_ERRORS.length)];
    const error = errorCreator();

    console.warn('[ErrorInjector] Throwing render-phase error:', error.message);
    throw error;
  }

  // Also record async errors directly via LDObserve.recordError()
  useEffect(() => {
    if (ERROR_INJECTION_ENABLED && Math.random() < ERROR_INJECTION_RATE * 0.3) {
      const error = new Error('Async operation failed unexpectedly');
      error.name = 'AsyncOperationError';

      setTimeout(() => {
        try {
          LDObserve.recordError(error, 'Frontend: Async operation error', {
            source: 'frontend',
            service: 'react-frontend',
            component: 'ErrorInjector',
            errorType: 'AsyncOperationError',
            demo_type: 'injected_async_error'
          });
          console.warn('[ErrorInjector] Recorded async error via LDObserve.recordError():', error.message);
        } catch (e) {
          console.error('[ErrorInjector] Failed to record async error:', e);
        }
      }, Math.random() * 2000); // Random delay within first 2 seconds
    }
  }, []);

  // This component renders nothing
  return null;
}

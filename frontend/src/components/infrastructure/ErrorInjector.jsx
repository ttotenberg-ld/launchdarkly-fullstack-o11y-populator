/**
 * ErrorInjector - A component that may inject errors during React's render cycle.
 * 
 * This component is designed for observability demo purposes. It randomly throws
 * errors during initial render to simulate real-world error scenarios that will
 * be captured by LaunchDarkly Observability.
 * 
 * The errors thrown here will:
 * 1. Be captured by the auto-instrumentation (window.onerror)
 * 2. Be caught by React Error Boundary (if one exists)
 * 3. Appear on the documentLoad span with has_errors=true
 */

import { useEffect, useRef } from 'react';

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

  // Only check on first mount
  if (!hasInjected.current && shouldInjectRenderError()) {
    hasInjected.current = true;
    
    // Pick a random error
    const errorCreator = RENDER_ERRORS[Math.floor(Math.random() * RENDER_ERRORS.length)];
    const error = errorCreator();
    
    console.warn('[ErrorInjector] Throwing render-phase error:', error.message);
    throw error;
  }

  // Also inject async errors occasionally
  useEffect(() => {
    if (ERROR_INJECTION_ENABLED && Math.random() < ERROR_INJECTION_RATE * 0.3) {
      // Inject an unhandled promise rejection
      const error = new Error('Async operation failed unexpectedly');
      error.name = 'AsyncOperationError';
      
      setTimeout(() => {
        console.warn('[ErrorInjector] Injecting async error:', error.message);
        Promise.reject(error);
      }, Math.random() * 2000); // Random delay within first 2 seconds
    }
  }, []);

  // This component renders nothing
  return null;
}

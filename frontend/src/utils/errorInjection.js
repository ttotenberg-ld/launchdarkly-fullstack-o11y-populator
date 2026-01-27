/**
 * Error injection utilities for generating realistic frontend errors.
 * These errors are designed to be captured by LaunchDarkly Observability auto-instrumentation
 * and will appear on the documentLoad span with has_errors=true.
 */

// Probability of injecting an error during page load (5% by default)
const ERROR_INJECTION_RATE = parseFloat(import.meta.env.VITE_ERROR_INJECTION_RATE || '0.05');

// Whether error injection is enabled
const ERROR_INJECTION_ENABLED = import.meta.env.VITE_ERROR_INJECTION_ENABLED !== 'false';

// Session-level error flag - if set, this session will have errors
// This ensures consistent error behavior within a single session
let sessionHasErrors = null;

/**
 * Determine if this session should have errors.
 * Called once per session (page load) and cached.
 */
function shouldSessionHaveErrors() {
  if (sessionHasErrors === null) {
    sessionHasErrors = ERROR_INJECTION_ENABLED && Math.random() < ERROR_INJECTION_RATE;
  }
  return sessionHasErrors;
}

/**
 * Reset session error state (for testing purposes).
 */
export function resetSessionErrorState() {
  sessionHasErrors = null;
}

/**
 * Error types that can be injected with realistic messages.
 */
const ERROR_TYPES = [
  {
    name: 'TypeError',
    create: () => new TypeError("Cannot read properties of undefined (reading 'map')"),
    phase: 'render',
  },
  {
    name: 'ReferenceError', 
    create: () => new ReferenceError('productData is not defined'),
    phase: 'render',
  },
  {
    name: 'NetworkError',
    create: () => new Error('Failed to fetch: Network request failed'),
    phase: 'async',
  },
  {
    name: 'ChunkLoadError',
    create: () => {
      const err = new Error('Loading chunk 5 failed.');
      err.name = 'ChunkLoadError';
      return err;
    },
    phase: 'load',
  },
  {
    name: 'SyntaxError',
    create: () => new SyntaxError('Unexpected token < in JSON at position 0'),
    phase: 'async',
  },
  {
    name: 'RangeError',
    create: () => new RangeError('Maximum call stack size exceeded'),
    phase: 'render',
  },
];

/**
 * Get a random error type.
 */
function getRandomError() {
  return ERROR_TYPES[Math.floor(Math.random() * ERROR_TYPES.length)];
}

/**
 * Inject a synchronous error during page load.
 * This will be captured by window.onerror and attached to the documentLoad span.
 */
export function maybeInjectLoadError() {
  if (!shouldSessionHaveErrors()) {
    return;
  }

  const errorConfig = getRandomError();
  
  // Use setTimeout with 0 delay to throw after current stack but still during load
  // This ensures the error is uncaught and captured by auto-instrumentation
  setTimeout(() => {
    console.warn('[ErrorInjection] Injecting simulated error for observability demo:', errorConfig.name);
    throw errorConfig.create();
  }, 0);
}

/**
 * Inject an unhandled promise rejection.
 * This will be captured by window.onunhandledrejection.
 */
export function maybeInjectUnhandledRejection() {
  if (!shouldSessionHaveErrors()) {
    return;
  }

  const errorConfig = getRandomError();
  
  // Create an unhandled promise rejection
  Promise.reject(errorConfig.create());
  console.warn('[ErrorInjection] Injecting unhandled rejection for observability demo:', errorConfig.name);
}

/**
 * React hook that may throw an error during component render.
 * Call this in a component to potentially inject an error during initial render.
 * 
 * @param {string} componentName - Name of the component for error context
 * @param {number} probability - Override probability (0-1), defaults to session rate
 */
export function useMaybeThrowError(componentName = 'Unknown', probability = null) {
  // Only throw on first render if this is an error session
  if (!shouldSessionHaveErrors()) {
    return;
  }

  // Additional per-component probability check if provided
  if (probability !== null && Math.random() >= probability) {
    return;
  }

  // Throw synchronously during render to be captured as an uncaught error
  // React's Error Boundary might catch this, but the error will still be recorded
  // by the auto-instrumentation before the boundary handles it
  const errorConfig = getRandomError();
  console.warn(`[ErrorInjection] Throwing error in ${componentName}:`, errorConfig.name);
  throw errorConfig.create();
}

/**
 * Initialize error injection on app startup.
 * This should be called early in the app initialization.
 */
export function initializeErrorInjection() {
  if (!ERROR_INJECTION_ENABLED) {
    console.log('[ErrorInjection] Error injection is disabled');
    return;
  }

  // Determine if this session will have errors
  const willHaveErrors = shouldSessionHaveErrors();
  
  if (willHaveErrors) {
    console.log(`[ErrorInjection] This session WILL have injected errors (rate: ${ERROR_INJECTION_RATE * 100}%)`);
    
    // Inject an error early in the page load
    maybeInjectLoadError();
  } else {
    console.log(`[ErrorInjection] This session will NOT have injected errors (rate: ${ERROR_INJECTION_RATE * 100}%)`);
  }
}

export default {
  initializeErrorInjection,
  maybeInjectLoadError,
  maybeInjectUnhandledRejection,
  useMaybeThrowError,
  resetSessionErrorState,
};

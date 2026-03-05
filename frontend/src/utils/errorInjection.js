/**
 * Error injection utilities for generating realistic frontend errors.
 *
 * Three error injection strategies:
 *
 * 1. documentLoad span errors (registerDocumentLoadErrorProcessor):
 *    Registers a custom OTel SpanProcessor that intercepts documentLoad spans
 *    when they're first created and directly adds exception events + error
 *    status. This embeds the error IN the span itself, giving us:
 *      span_name="documentLoad" has_errors=true
 *
 *    Why a SpanProcessor? The OTel document-load instrumentation creates the
 *    documentLoad span in a deferred setTimeout after the 'load' event.
 *    Errors thrown during the load event create separate root spans (not
 *    children of documentLoad). A SpanProcessor's onStart() fires when the
 *    span is first created (still open), letting us call recordException()
 *    and setStatus(ERROR) directly on the span.
 *
 * 2. documentLoad window errors (setupDocumentLoadErrors):
 *    Throws uncaught errors during the window 'load' event as a secondary
 *    mechanism. The SDK's window.onerror handler catches these and creates
 *    highlight.exception spans with timestamps during the documentLoad
 *    time window, which may help with server-side time-based correlation.
 *
 * 3. Post-load errors (initializeErrorInjection, useMaybeThrowError):
 *    Records errors via LDObserve.recordError() or throws in React render
 *    (caught by ErrorBoundary). These create session-level errors but are
 *    NOT on the documentLoad span.
 */

import { LDObserve } from '@launchdarkly/observability';

// Probability of injecting an error during page load (25% by default)
const ERROR_INJECTION_RATE = parseFloat(import.meta.env.VITE_ERROR_INJECTION_RATE || '0.25');

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
    name: 'DataError',
    create: () => new Error('Invalid response format: expected JSON, received HTML'),
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
 * Record an error directly with LDObserve.recordError().
 * This matches the reference implementation's pattern of catching errors
 * and explicitly recording them, ensuring they appear on the documentLoad span.
 */
function recordInjectedError(errorConfig, context) {
  try {
    const error = errorConfig.create();
    LDObserve.recordError(error, `Frontend: ${error.message}`, {
      source: 'frontend',
      service: 'react-frontend',
      errorType: errorConfig.name,
      component: context,
      demo_type: 'injected_error'
    });
    console.warn(`[ErrorInjection] Recorded ${errorConfig.name} via LDObserve.recordError():`, error.message);
  } catch (e) {
    console.error('[ErrorInjection] Failed to record error (SDK not ready?):', e);
  }
}

/**
 * Inject an error during page load by recording it directly with the SDK.
 */
export function maybeInjectLoadError() {
  if (!shouldSessionHaveErrors()) {
    return;
  }

  const errorConfig = getRandomError();
  recordInjectedError(errorConfig, 'pageLoad');
}

/**
 * Inject an unhandled promise rejection error by recording it directly with the SDK.
 */
export function maybeInjectUnhandledRejection() {
  if (!shouldSessionHaveErrors()) {
    return;
  }

  const errorConfig = getRandomError();
  recordInjectedError(errorConfig, 'asyncOperation');
}

/**
 * React hook that may throw an error during component render.
 * These render-phase throws are caught by the ErrorBoundary, which
 * calls LDObserve.recordError() in componentDidCatch.
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

  // Throw synchronously during render - caught by ErrorBoundary which
  // calls LDObserve.recordError() in componentDidCatch
  const errorConfig = getRandomError();
  console.warn(`[ErrorInjection] Throwing error in ${componentName}:`, errorConfig.name);
  throw errorConfig.create();
}

/**
 * Access the OTel TracerProvider from the global registry.
 *
 * The LD Observability SDK bundles the OTel API and registers the
 * TracerProvider globally via Symbol.for('opentelemetry.js.api.1').
 * We access it to add a custom SpanProcessor without needing to install
 * @opentelemetry/api as a separate dependency.
 */
function getTracerProvider() {
  try {
    // OTel API v1.x stores globals at this well-known Symbol key
    const api = globalThis[Symbol.for('opentelemetry.js.api.1')];
    if (!api?.trace) return null;

    // The trace API exposes a ProxyTracerProvider wrapping the real provider
    const proxyProvider = typeof api.trace.getTracerProvider === 'function'
      ? api.trace.getTracerProvider()
      : api.trace._proxyTracerProvider;

    if (!proxyProvider) return null;

    // Get the real BasicTracerProvider (which has addSpanProcessor)
    const delegate = (typeof proxyProvider.getDelegate === 'function'
      ? proxyProvider.getDelegate()
      : proxyProvider._delegate);

    if (delegate && typeof delegate.addSpanProcessor === 'function') {
      return delegate;
    }

    // Fallback: maybe proxyProvider itself supports addSpanProcessor
    if (typeof proxyProvider.addSpanProcessor === 'function') {
      return proxyProvider;
    }

    return null;
  } catch (e) {
    console.warn('[ErrorInjection] Error accessing OTel TracerProvider:', e);
    return null;
  }
}

/**
 * Register a custom OTel SpanProcessor that injects errors directly onto
 * documentLoad spans.
 *
 * The OTel document-load instrumentation creates the documentLoad span in
 * a deferred setTimeout after the window 'load' event. Our SpanProcessor's
 * onStart() fires when the span is first created (still open), allowing us
 * to call recordException() and setStatus(ERROR) directly on it.
 *
 * This is the most reliable way to get has_errors=true on documentLoad
 * spans because the error is embedded IN the span itself, not just
 * temporally correlated.
 *
 * IMPORTANT: Must be called AFTER asyncWithLDProvider() is invoked (which
 * synchronously creates the TracerProvider) but BEFORE the load event fires
 * (which triggers documentLoad span creation via setTimeout).
 */
export function registerDocumentLoadErrorProcessor() {
  if (!ERROR_INJECTION_ENABLED) return;
  if (!shouldSessionHaveErrors()) {
    console.log('[ErrorInjection] Session will not have documentLoad errors');
    return;
  }

  const tracerProvider = getTracerProvider();
  if (!tracerProvider) {
    console.warn(
      '[ErrorInjection] Could not access OTel TracerProvider — ' +
      'documentLoad error injection will rely on fallback (thrown errors during load event)'
    );
    return;
  }

  // Pre-select the error to inject (deterministic per session)
  const errorCreator = DOCUMENT_LOAD_ERRORS[
    Math.floor(Math.random() * DOCUMENT_LOAD_ERRORS.length)
  ];
  let injected = false;

  tracerProvider.addSpanProcessor({
    onStart(span) {
      // Only inject once per session, only on documentLoad spans
      if (injected) return;
      if (span.name !== 'documentLoad') return;

      const error = errorCreator();

      // Record the exception event on the span (adds 'exception' event
      // with exception.type, exception.message, exception.stacktrace)
      if (typeof span.recordException === 'function') {
        span.recordException(error);
      }

      // Set span status to ERROR so has_errors=true is computed
      if (typeof span.setStatus === 'function') {
        span.setStatus({ code: 2, message: error.message }); // 2 = SpanStatusCode.ERROR
      }

      injected = true;
      console.warn('[ErrorInjection] Injected error onto documentLoad span:', error.message);
    },
    onEnd() {},
    shutdown() { return Promise.resolve(); },
    forceFlush() { return Promise.resolve(); },
  });

  console.log('[ErrorInjection] DocumentLoad error SpanProcessor registered');
}

/**
 * Error types that realistically occur during page load / document loading.
 * Used by both the SpanProcessor (primary) and the load-event throw (fallback).
 */
const DOCUMENT_LOAD_ERRORS = [
  () => new TypeError("Cannot read properties of null (reading 'appendChild')"),
  () => {
    const err = new Error("Loading CSS chunk styles-vendor failed.");
    err.name = 'ChunkLoadError';
    return err;
  },
  () => new ReferenceError('__INITIAL_STATE__ is not defined'),
  () => new SyntaxError("Unexpected token '<' in JSON at position 0"),
  () => new TypeError("Cannot set properties of undefined (setting 'innerHTML')"),
  () => {
    const err = new Error('Hydration failed because the initial UI does not match what was rendered on the server.');
    err.name = 'HydrationError';
    return err;
  },
];

/**
 * Set up error injection during the documentLoad time window (fallback).
 *
 * Registers a window 'load' event handler that throws uncaught errors.
 * The SDK's window.onerror handler catches these and creates
 * highlight.exception spans with timestamps that fall within the
 * documentLoad time window (fetchStart → loadEventEnd). The server
 * may use time-based correlation to associate these with the
 * documentLoad span.
 *
 * NOTE: These highlight.exception spans are ROOT spans (not children of
 * documentLoad) because the documentLoad span doesn't exist yet when our
 * handler fires — the SDK creates it in a deferred setTimeout. The primary
 * mechanism is registerDocumentLoadErrorProcessor() which directly embeds
 * errors IN the documentLoad span via a SpanProcessor.
 *
 * IMPORTANT: Must be called BEFORE asyncWithLDProvider() to ensure the
 * listener is registered before the load event fires.
 */
export function setupDocumentLoadErrors() {
  if (!ERROR_INJECTION_ENABLED) return;

  window.addEventListener('load', () => {
    if (!shouldSessionHaveErrors()) return;

    const errorCreator = DOCUMENT_LOAD_ERRORS[Math.floor(Math.random() * DOCUMENT_LOAD_ERRORS.length)];
    const error = errorCreator();

    console.warn('[ErrorInjection] Throwing documentLoad error:', error.message);

    // Throw uncaught → browser calls window.onerror → SDK catches it →
    // highlight.exception span created as child of active documentLoad span.
    // This is safe: throwing in an event listener doesn't prevent other
    // listeners from running (the browser catches it and continues).
    throw error;
  });
}

/**
 * Initialize post-load error injection on app startup.
 * This should be called after the Observability SDK is initialized.
 * These errors appear on sessions but NOT on documentLoad spans.
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

    // Record an error directly via LDObserve.recordError()
    maybeInjectLoadError();
  } else {
    console.log(`[ErrorInjection] This session will NOT have injected errors (rate: ${ERROR_INJECTION_RATE * 100}%)`);
  }
}

export default {
  initializeErrorInjection,
  registerDocumentLoadErrorProcessor,
  setupDocumentLoadErrors,
  maybeInjectLoadError,
  maybeInjectUnhandledRejection,
  useMaybeThrowError,
  resetSessionErrorState,
};

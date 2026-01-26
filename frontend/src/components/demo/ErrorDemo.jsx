import { useState } from 'react';
import { LDObserve } from '@launchdarkly/observability';
import { showToast } from '../infrastructure/Toast';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

function ErrorDemo() {
  const [shouldThrowError, setShouldThrowError] = useState(false);

  // This will trigger the Error Boundary
  if (shouldThrowError) {
    throw new Error('This is a deliberate error to test the Error Boundary!');
  }

  const handleManualError = async () => {
    try {
      const response = await fetch(`${API_URL}/api/errors/manual`);
      const data = await response.json();
      console.log('Manual error response:', data);
      showToast(`Manual error recorded on backend! Error: ${data.error_message}`, 'success');
    } catch (error) {
      console.error('Failed to call backend:', error);
      showToast('Failed to call backend API. Make sure the backend server is running.', 'error');
    }
  };

  const handleAsyncError = async () => {
    try {
      const response = await fetch(`${API_URL}/api/errors/async`);
      const data = await response.json();
      console.log('Async error response:', data);
      showToast(`Async error recorded on backend! Error: ${data.error_message}`, 'success');
    } catch (error) {
      console.error('Failed to call backend:', error);
      showToast('Failed to call backend API. Make sure the backend server is running.', 'error');
    }
  };

  const handleUncaughtError = async () => {
    try {
      const response = await fetch(`${API_URL}/api/errors/uncaught`);
      const data = await response.json();
      console.log('Uncaught error response:', data);
      showToast(`Uncaught error recorded on backend! Error: ${data.error_message}`, 'success');
    } catch (error) {
      console.error('Failed to call backend:', error);
      showToast('Failed to call backend API. Make sure the backend server is running.', 'error');
    }
  };

  const handleFrontendError = () => {
    try {
      // Manually throw and catch an error for frontend demonstration
      throw new Error('Manually triggered frontend error for demonstration');
    } catch (error) {
      // Record error to LaunchDarkly Observability with clear frontend attribution
      LDObserve.recordError(error, 'Frontend: Manual error from button click', {
        source: 'frontend',
        service: 'react-frontend',
        component: 'ErrorDemo.jsx',
        errorType: error.name || 'Error',
        demo_type: 'manual_frontend_error'
      });
      console.error('Frontend error recorded:', error);
      showToast('Frontend error recorded! Check the console and LaunchDarkly dashboard.', 'success');
    }
  };

  const handleFrontendUncaughtError = () => {
    // This will trigger the Error Boundary
    setShouldThrowError(true);
  };

  const handleBothErrors = async () => {
    try {
      // First, trigger a backend error
      const response = await fetch(`${API_URL}/api/errors/manual`);
      const data = await response.json();
      console.log('Backend error recorded:', data);
      
      // Then trigger a frontend error
      // Adding a small delay to ensure backend error is recorded first
      setTimeout(() => {
        try {
          throw new Error('Frontend error triggered after backend error');
        } catch (error) {
          LDObserve.recordError(error, 'Frontend: Error in combined test', {
            source: 'frontend',
            service: 'react-frontend',
            component: 'ErrorDemo.jsx',
            demo_type: 'combined_frontend_error',
            triggered_after_backend: true
          });
          console.error('Frontend error recorded:', error);
          showToast('Both backend and frontend errors recorded! Check LaunchDarkly dashboard.', 'success');
        }
      }, 100);
    } catch (error) {
      console.error('Failed to call backend:', error);
      // Still throw frontend error even if backend call fails
      setTimeout(() => {
        try {
          throw new Error('Frontend error (backend call failed)');
        } catch (error) {
          LDObserve.recordError(error, 'Frontend: Error when backend unavailable', {
            source: 'frontend',
            service: 'react-frontend',
            component: 'ErrorDemo.jsx',
            demo_type: 'frontend_error_fallback'
          });
        }
      }, 100);
    }
  };

  return (
    <div className="card">
      <h2>🐛 Error Tracking Demo</h2>
      <p>
        Test different types of error tracking from both frontend and backend. All errors are recorded 
        and sent to LaunchDarkly Observability with clear <strong>source attribution</strong> (frontend vs backend).
      </p>

      <div className="button-group">
        <button onClick={handleManualError}>
          Backend: Manual Error
        </button>
        
        <button onClick={handleAsyncError}>
          Backend: Async Error
        </button>
        
        <button onClick={handleUncaughtError}>
          Backend: Uncaught Error
        </button>

        <button 
          onClick={handleFrontendError}
          style={{ backgroundColor: '#ff6b6b' }}
        >
          Frontend: Manual Error
        </button>

        <button 
          onClick={handleFrontendUncaughtError}
          style={{ backgroundColor: '#e74c3c' }}
        >
          Frontend: React Error Boundary
        </button>

        <button 
          onClick={handleBothErrors}
          style={{ backgroundColor: '#d9534f', fontWeight: 'bold' }}
        >
          🚨 Both: Frontend + Backend
        </button>
      </div>

      <details style={{ marginTop: '20px', fontSize: '14px' }}>
        <summary style={{ cursor: 'pointer', fontWeight: '600', color: '#555', marginBottom: '10px' }}>
          View API Usage & Examples
        </summary>
        
        {/* Frontend Example */}
        <div style={{ 
          marginTop: '15px', 
          padding: '15px', 
          backgroundColor: '#fff8e1',
          borderRadius: '8px',
          fontSize: '14px',
          borderLeft: '4px solid #ffc107'
        }}>
          <strong>🌐 Frontend (JavaScript/React):</strong>
          <pre style={{ 
            marginTop: '10px',
            padding: '12px',
            backgroundColor: '#fff',
            borderRadius: '4px',
            border: '1px solid #ddd',
            overflow: 'auto'
          }}>
{`// In your React Error Boundary
componentDidCatch(error, errorInfo) {
  LDObserve.recordError(error, 'React component error', {
    source: 'frontend',
    service: 'react-frontend',
    component: 'ErrorBoundary',
    componentStack: errorInfo.componentStack
  });
}

// Or manually catch and record errors
try {
  throw new Error('Something went wrong');
} catch (error) {
  LDObserve.recordError(error, 'Manual error', {
    source: 'frontend',
    component: 'MyComponent.jsx'
  });
}`}
          </pre>
          <p style={{ marginTop: '10px', color: '#666' }}>
            <strong>Parameters:</strong>
          </p>
          <ul style={{ marginLeft: '20px', color: '#666', lineHeight: '1.8' }}>
            <li><strong>error</strong> (Error): The error object to record</li>
            <li><strong>message</strong> (string): Descriptive message about the error context</li>
            <li><strong>attributes</strong> (object): Additional metadata like component stack</li>
            <li><strong>source</strong> (attribute): Set to 'frontend' to identify frontend errors</li>
          </ul>
        </div>

        {/* Backend Example */}
        <div style={{ 
          marginTop: '15px', 
          padding: '15px', 
          backgroundColor: '#f8f9fa',
          borderRadius: '8px',
          fontSize: '14px',
          borderLeft: '4px solid #6c757d'
        }}>
          <strong>🔧 Backend (Python):</strong>
          <pre style={{ 
            marginTop: '10px',
            padding: '12px',
            backgroundColor: '#fff',
            borderRadius: '4px',
            border: '1px solid #ddd',
            overflow: 'auto'
          }}>
{`# In your Flask/Python backend
from ldobserve.observe import record_exception

try:
    # Your operation here
    result = perform_operation()
except Exception as error:
    record_exception(
        error,
        {
            'source': 'backend',
            'service': 'python-backend',
            'endpoint': '/api/errors/manual',
            'demo_type': 'manual_error',
            'message': 'Operation failed'
        }
    )
    raise`}
          </pre>
          <p style={{ marginTop: '10px', color: '#666' }}>
            <strong>Parameters:</strong>
          </p>
          <ul style={{ marginLeft: '20px', color: '#666', lineHeight: '1.8' }}>
            <li><strong>error</strong> (Exception): The Python exception object</li>
            <li><strong>attributes</strong> (dict): Additional metadata for debugging</li>
            <li><strong>source</strong> (attribute): Set to 'backend' to identify backend errors</li>
          </ul>
        </div>

        <div style={{ 
          marginTop: '15px', 
          padding: '15px', 
          backgroundColor: '#fff3e0',
          borderRadius: '8px',
          fontSize: '14px',
          borderLeft: '4px solid #ff9800'
        }}>
          <strong>What's being tracked:</strong>
          <ul style={{ marginTop: '10px', marginLeft: '20px', lineHeight: '1.8' }}>
            <li><strong>Backend: Manual Error:</strong> Caught error with custom context and metadata (source: backend)</li>
            <li><strong>Backend: Async Error:</strong> Error from asynchronous operations (source: backend)</li>
            <li><strong>Backend: Uncaught Error:</strong> Error caught by Flask's global error handler (source: backend)</li>
            <li><strong>Frontend: Manual Error:</strong> Caught error with custom context (source: frontend)</li>
            <li><strong>Frontend: React Error:</strong> Error caught by React Error Boundary (source: frontend)</li>
            <li><strong>Both:</strong> Triggers backend error first, then frontend error (demonstrates both sources)</li>
          </ul>
          <p style={{ marginTop: '10px', color: '#666' }}>
            All errors include a <code style={{ backgroundColor: '#f0f0f0', padding: '2px 6px', borderRadius: '3px' }}>source</code> attribute 
            (<code style={{ backgroundColor: '#f0f0f0', padding: '2px 6px', borderRadius: '3px' }}>frontend</code> or <code style={{ backgroundColor: '#f0f0f0', padding: '2px 6px', borderRadius: '3px' }}>backend</code>) 
            to clearly identify where the error originated.
          </p>
        </div>
      </details>
    </div>
  );
}

export default ErrorDemo;

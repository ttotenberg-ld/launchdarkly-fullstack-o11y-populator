import { LDObserve } from '@launchdarkly/observability';
import { showToast } from '../infrastructure/Toast';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

function LogsDemo() {
  const handleDebugLog = () => {
    LDObserve.recordLog('Frontend: Debug log message', 'debug', {
      source: 'frontend',
      service: 'react-frontend',
      component: 'LogsDemo.jsx',
      timestamp: new Date().toISOString()
    });
    console.log('Frontend debug log sent to LaunchDarkly');
    showToast('Frontend Debug log recorded! Check LaunchDarkly dashboard.', 'success');
  };

  const handleInfoLog = () => {
    LDObserve.recordLog('Frontend: Info log message', 'info', {
      source: 'frontend',
      service: 'react-frontend',
      component: 'LogsDemo.jsx',
      timestamp: new Date().toISOString()
    });
    console.log('Frontend info log sent to LaunchDarkly');
    showToast('Frontend Info log recorded! Check LaunchDarkly dashboard.', 'success');
  };

  const handleWarnLog = () => {
    LDObserve.recordLog('Frontend: Warning log message', 'warn', {
      source: 'frontend',
      service: 'react-frontend',
      component: 'LogsDemo.jsx',
      timestamp: new Date().toISOString()
    });
    console.log('Frontend warning log sent to LaunchDarkly');
    showToast('Frontend Warning log recorded! Check LaunchDarkly dashboard.', 'success');
  };

  const handleErrorLog = () => {
    LDObserve.recordLog('Frontend: Error log message', 'error', {
      source: 'frontend',
      service: 'react-frontend',
      component: 'LogsDemo.jsx',
      timestamp: new Date().toISOString()
    });
    console.log('Frontend error log sent to LaunchDarkly');
    showToast('Frontend Error log recorded! Check LaunchDarkly dashboard.', 'success');
  };

  const handleBackendDebugLog = async () => {
    try {
      const response = await fetch(`${API_URL}/api/logs/debug`);
      const data = await response.json();
      console.log('Backend debug log response:', data);
      showToast('Backend Debug log recorded! Check LaunchDarkly dashboard.', 'success');
    } catch (error) {
      console.error('Failed to call backend:', error);
      showToast('Failed to call backend API. Make sure the backend server is running.', 'error');
    }
  };

  const handleBackendInfoLog = async () => {
    try {
      const response = await fetch(`${API_URL}/api/logs/info`);
      const data = await response.json();
      console.log('Backend info log response:', data);
      showToast('Backend Info log recorded! Check LaunchDarkly dashboard.', 'success');
    } catch (error) {
      console.error('Failed to call backend:', error);
      showToast('Failed to call backend API. Make sure the backend server is running.', 'error');
    }
  };

  const handleBackendWarnLog = async () => {
    try {
      const response = await fetch(`${API_URL}/api/logs/warn`);
      const data = await response.json();
      console.log('Backend warning log response:', data);
      showToast('Backend Warning log recorded! Check LaunchDarkly dashboard.', 'success');
    } catch (error) {
      console.error('Failed to call backend:', error);
      showToast('Failed to call backend API. Make sure the backend server is running.', 'error');
    }
  };

  const handleBackendErrorLog = async () => {
    try {
      const response = await fetch(`${API_URL}/api/logs/error`);
      const data = await response.json();
      console.log('Backend error log response:', data);
      showToast('Backend Error log recorded! Check LaunchDarkly dashboard.', 'success');
    } catch (error) {
      console.error('Failed to call backend:', error);
      showToast('Failed to call backend API. Make sure the backend server is running.', 'error');
    }
  };

  return (
    <div className="card">
      <h2>📝 Custom Logs Demo</h2>
      <p>
        Send custom log messages from both frontend and backend to LaunchDarkly at different severity levels.
        All logs include clear <strong>source attribution</strong> (frontend vs backend).
      </p>

      <div style={{ marginTop: '20px' }}>
        <h3 style={{ marginBottom: '15px', color: '#333' }}>Frontend Log Levels</h3>
        <div className="button-group">
          <button 
            onClick={handleDebugLog}
            style={{ backgroundColor: '#9e9e9e' }}
          >
            Frontend: Debug Log
          </button>
          
          <button 
            onClick={handleInfoLog}
            style={{ backgroundColor: '#2196f3' }}
          >
            Frontend: Info Log
          </button>
          
          <button 
            onClick={handleWarnLog}
            style={{ backgroundColor: '#ff9800' }}
          >
            Frontend: Warning Log
          </button>
          
          <button 
            onClick={handleErrorLog}
            style={{ backgroundColor: '#d9534f' }}
          >
            Frontend: Error Log
          </button>
        </div>
      </div>

      <div style={{ marginTop: '30px' }}>
        <h3 style={{ marginBottom: '15px', color: '#333' }}>Backend Log Levels</h3>
        <div className="button-group">
          <button 
            onClick={handleBackendDebugLog}
            style={{ backgroundColor: '#757575' }}
          >
            Backend: Debug Log
          </button>
          
          <button 
            onClick={handleBackendInfoLog}
            style={{ backgroundColor: '#1976d2' }}
          >
            Backend: Info Log
          </button>
          
          <button 
            onClick={handleBackendWarnLog}
            style={{ backgroundColor: '#f57c00' }}
          >
            Backend: Warning Log
          </button>
          
          <button 
            onClick={handleBackendErrorLog}
            style={{ backgroundColor: '#c62828' }}
          >
            Backend: Error Log
          </button>
        </div>
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
          <strong>🌐 Frontend (JavaScript):</strong>
          <pre style={{ 
            marginTop: '10px',
            padding: '12px',
            backgroundColor: '#fff',
            borderRadius: '4px',
            border: '1px solid #ddd',
            overflow: 'auto'
          }}>
{`// Log with severity level
LDObserve.recordLog('User action performed', 'info', {
  source: 'frontend',
  service: 'react-frontend',
  action: 'button_click',
  component: 'MyComponent'
});

// Available severity levels
LDObserve.recordLog('Debug message', 'debug', { source: 'frontend' });
LDObserve.recordLog('Info message', 'info', { source: 'frontend' });
LDObserve.recordLog('Warning message', 'warn', { source: 'frontend' });
LDObserve.recordLog('Error message', 'error', { source: 'frontend' });`}
          </pre>
          <p style={{ marginTop: '10px', color: '#666' }}>
            <strong>Parameters:</strong>
          </p>
          <ul style={{ marginLeft: '20px', color: '#666', lineHeight: '1.8' }}>
            <li><strong>message</strong> (string): The log message to record</li>
            <li><strong>severity</strong>: 'debug' | 'info' | 'warn' | 'error'</li>
            <li><strong>attributes</strong> (object): Additional metadata (optional)</li>
            <li><strong>source</strong> (attribute): Set to 'frontend' to identify frontend logs</li>
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
{`# Python logging with LaunchDarkly
from ldobserve.observe import record_log, LEVELS

record_log('Processing request', LEVELS['info'], {
    'source': 'backend',
    'service': 'python-backend',
    'endpoint': '/api/data',
    'timestamp': time.time()
})

# Available severity levels
record_log('Debug message', LEVELS['debug'], {'source': 'backend'})
record_log('Info message', LEVELS['info'], {'source': 'backend'})
record_log('Warning message', LEVELS['warning'], {'source': 'backend'})
record_log('Error message', LEVELS['error'], {'source': 'backend'})`}
          </pre>
          <p style={{ marginTop: '10px', color: '#666' }}>
            <strong>Parameters:</strong>
          </p>
          <ul style={{ marginLeft: '20px', color: '#666', lineHeight: '1.8' }}>
            <li><strong>message</strong> (str): The log message to record</li>
            <li><strong>severity</strong>: LEVELS['debug'] | LEVELS['info'] | LEVELS['warning'] | LEVELS['error']</li>
            <li><strong>attributes</strong> (dict): Additional metadata (optional)</li>
            <li><strong>source</strong> (attribute): Set to 'backend' to identify backend logs</li>
          </ul>
        </div>

        <div style={{ 
          marginTop: '15px', 
          padding: '15px', 
          backgroundColor: '#e3f2fd',
          borderRadius: '8px',
          fontSize: '14px',
          borderLeft: '4px solid #2196f3'
        }}>
          <strong>💡 When to use each severity level:</strong>
          <ul style={{ marginTop: '10px', marginLeft: '20px', lineHeight: '1.8' }}>
            <li><strong>debug:</strong> Detailed diagnostic information for troubleshooting</li>
            <li><strong>info:</strong> General informational messages about application flow</li>
            <li><strong>warn:</strong> Warning messages for potentially harmful situations</li>
            <li><strong>error:</strong> Error events that might still allow the application to continue</li>
          </ul>
          <p style={{ marginTop: '10px', color: '#666' }}>
            All logs include a <code style={{ backgroundColor: '#f0f0f0', padding: '2px 6px', borderRadius: '3px' }}>source</code> attribute 
            (<code style={{ backgroundColor: '#f0f0f0', padding: '2px 6px', borderRadius: '3px' }}>frontend</code> or <code style={{ backgroundColor: '#f0f0f0', padding: '2px 6px', borderRadius: '3px' }}>backend</code>) 
            to clearly identify where the log originated.
          </p>
        </div>
      </details>
    </div>
  );
}

export default LogsDemo;

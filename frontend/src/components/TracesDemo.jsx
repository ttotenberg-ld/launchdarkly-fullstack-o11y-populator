import { useState } from 'react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

function TracesDemo() {
  const [autoResult, setAutoResult] = useState(null);
  const [manualResult, setManualResult] = useState(null);
  const [manualProgress, setManualProgress] = useState('');

  const handleAutomaticSpan = async () => {
    setAutoResult('Processing...');
    
    try {
      // Call Python backend which creates an automatic span
      const response = await fetch(`${API_URL}/api/traces/simple`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      const data = await response.json();
      
      if (data.success) {
        setAutoResult(data.message);
      } else {
        setAutoResult('✗ Error processing request');
      }
    } catch (error) {
      console.error('Failed to call backend:', error);
      setAutoResult('✗ Failed to connect to backend');
      alert('Failed to call backend API. Make sure the backend server is running.');
    }
  };

  const handleManualSpan = async () => {
    setManualResult('Processing...');
    setManualProgress('Calling backend...');
    
    try {
      // Call Python backend which creates a manual span with multiple steps
      const response = await fetch(`${API_URL}/api/traces/multi-step`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      const data = await response.json();
      
      if (data.success) {
        // Simulate showing progress (backend processes all steps)
        setManualProgress('Processing on backend...');
        await new Promise(resolve => setTimeout(resolve, 500));
        
        setManualResult(data.message);
        setManualProgress('');
      } else {
        setManualResult(`✗ ${data.message}`);
        setManualProgress('');
      }
    } catch (error) {
      console.error('Failed to call backend:', error);
      setManualResult('✗ Failed to connect to backend');
      setManualProgress('');
      alert('Failed to call backend API. Make sure the backend server is running.');
    }
  };

  return (
    <div className="card">
      <h2>🔍 Traces Demo</h2>
      <p>
        Create trace spans in the Python backend to track operations. These examples demonstrate
        automatic vs. manual span management with distributed tracing from frontend to backend.
      </p>

      {/* Automatic Span Example */}
      <div style={{ marginTop: '20px', marginBottom: '30px' }}>
        <h3 style={{ marginBottom: '10px', color: '#333' }}>
          Example 1: Automatic Span (Python Backend)
        </h3>
        <p style={{ fontSize: '14px', color: '#666', marginBottom: '15px' }}>
          Backend uses Python context managers for automatic span management. The span ends when the context exits.
        </p>
        
        <button onClick={handleAutomaticSpan} style={{ backgroundColor: '#2196f3' }}>
          Run Simple API Fetch
        </button>
        
        {autoResult && (
          <div style={{
            marginTop: '15px',
            padding: '12px',
            backgroundColor: autoResult.startsWith('✓') ? '#e8f5e9' : '#fff3e0',
            borderRadius: '6px',
            borderLeft: `4px solid ${autoResult.startsWith('✓') ? '#4caf50' : '#ff9800'}`,
            fontSize: '14px'
          }}>
            {autoResult}
          </div>
        )}
        
        <details style={{ marginTop: '15px', fontSize: '14px' }}>
          <summary style={{ cursor: 'pointer', fontWeight: '600', color: '#555', marginBottom: '10px' }}>
            View API Usage & Examples
          </summary>
          
          <div style={{ 
            marginTop: '15px', 
            padding: '15px', 
            backgroundColor: '#f8f9fa',
            borderRadius: '8px',
            fontSize: '14px'
          }}>
            <strong>Python API Usage:</strong>
            <pre style={{ 
              marginTop: '10px',
              padding: '12px',
              backgroundColor: '#fff',
              borderRadius: '4px',
              border: '1px solid #ddd',
              overflow: 'auto'
            }}>
{`with ldobserve.start_span('operation.name') as span:
    span.set_attribute('key', 'value')
    # Your operation here
    # Span ends automatically when context exits`}
            </pre>
            <p style={{ marginTop: '10px', color: '#666' }}>
              <strong>Parameters:</strong>
            </p>
            <ul style={{ marginLeft: '20px', color: '#666', lineHeight: '1.8' }}>
              <li><strong>name</strong> (string): Name of the span operation</li>
              <li><strong>callback</strong> (function): Async function that receives the span object</li>
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
            <strong>💡 Example Implementation:</strong>
            <pre style={{ 
              marginTop: '10px',
              padding: '12px',
              backgroundColor: '#fff',
              borderRadius: '4px',
              border: '1px solid #ddd',
              overflow: 'auto'
            }}>
{`# Span ends automatically when context exits
with ldobserve.start_span('api.fetch.simple') as span:
    span.set_attribute('operation.type', 'simple_fetch')
    
    # Simulate API processing
    time.sleep(0.8)
    
    span.set_attribute('response.status', 200)
    span.set_attribute('response.title', 'Data loaded successfully')
    
    # Span ends here automatically`}
            </pre>
          </div>
        </details>
      </div>

      <hr style={{ margin: '30px 0', border: 'none', borderTop: '1px solid #ddd' }} />

      {/* Manual Span Example */}
      <div style={{ marginTop: '30px', marginBottom: '20px' }}>
        <h3 style={{ marginBottom: '10px', color: '#333' }}>
          Example 2: Manual Span (Python Backend)
        </h3>
        <p style={{ fontSize: '14px', color: '#666', marginBottom: '15px' }}>
          Backend uses Python context managers for manual span control. Perfect for complex workflows with multiple steps
          where you want to track progress throughout the operation.
        </p>
        
        <button onClick={handleManualSpan} style={{ backgroundColor: '#9c27b0' }}>
          Run Multi-Step Workflow
        </button>
        
        {manualProgress && (
          <div style={{
            marginTop: '15px',
            padding: '12px',
            backgroundColor: '#e3f2fd',
            borderRadius: '6px',
            borderLeft: '4px solid #2196f3',
            fontSize: '14px',
            fontWeight: '600'
          }}>
            ⏳ {manualProgress}
          </div>
        )}
        
        {manualResult && !manualProgress && (
          <div style={{
            marginTop: '15px',
            padding: '12px',
            backgroundColor: manualResult.startsWith('✓') ? '#e8f5e9' : '#ffebee',
            borderRadius: '6px',
            borderLeft: `4px solid ${manualResult.startsWith('✓') ? '#4caf50' : '#f44336'}`,
            fontSize: '14px'
          }}>
            {manualResult}
          </div>
        )}
        
        <details style={{ marginTop: '15px', fontSize: '14px' }}>
          <summary style={{ cursor: 'pointer', fontWeight: '600', color: '#555', marginBottom: '10px' }}>
            View API Usage & Examples
          </summary>
          
          <div style={{ 
            marginTop: '15px', 
            padding: '15px', 
            backgroundColor: '#f8f9fa',
            borderRadius: '8px',
            fontSize: '14px'
          }}>
            <strong>Python API Usage:</strong>
            <pre style={{ 
              marginTop: '10px',
              padding: '12px',
              backgroundColor: '#fff',
              borderRadius: '4px',
              border: '1px solid #ddd',
              overflow: 'auto'
            }}>
{`with ldobserve.start_manual_span('operation.name') as span:
    try:
        span.set_attribute('key', 'value')
        # Your operation here
    except Exception as error:
        span.set_status_error(str(error))
        raise`}
            </pre>
            <p style={{ marginTop: '10px', color: '#666' }}>
              <strong>Parameters:</strong>
            </p>
            <ul style={{ marginLeft: '20px', color: '#666', lineHeight: '1.8' }}>
              <li><strong>name</strong> (string): Name of the span operation</li>
              <li><strong>Context manager</strong>: Automatically manages span lifecycle</li>
            </ul>
            <p style={{ marginTop: '10px', color: '#666' }}>
              <strong>Note:</strong> Python context managers automatically handle span ending.
            </p>
          </div>

          <div style={{ 
            marginTop: '15px', 
            padding: '15px', 
            backgroundColor: '#e3f2fd',
            borderRadius: '8px',
            fontSize: '14px',
            borderLeft: '4px solid #2196f3'
          }}>
            <strong>💡 Example Implementation:</strong>
            <pre style={{ 
              marginTop: '10px',
              padding: '12px',
              backgroundColor: '#fff',
              borderRadius: '4px',
              border: '1px solid #ddd',
              overflow: 'auto'
            }}>
{`# Manual span with multiple steps
with ldobserve.start_manual_span('workflow.multi_step') as span:
    completed_steps = 0
    
    try:
        span.set_attribute('workflow.total_steps', 3)
        
        # Step 1
        time.sleep(0.6)
        completed_steps = 1
        span.set_attribute('step.1.completed', True)
        
        # Step 2
        time.sleep(0.6)
        completed_steps = 2
        span.set_attribute('step.2.completed', True)
        
        # Step 3
        time.sleep(0.6)
        completed_steps = 3
        span.set_attribute('step.3.completed', True)
        
        span.set_status_ok()
        # Result: Completed 3/3 steps!
    except Exception as error:
        span.set_status_error(str(error))
        
        # Record error
        ldobserve.record_error(error, 'Workflow failed', {
            'completed_steps': completed_steps
        })`}
            </pre>
          </div>
        </details>
      </div>

      {/* Key Differences */}
      <div style={{ 
        marginTop: '30px', 
        padding: '15px', 
        backgroundColor: '#f8f9fa',
        borderRadius: '8px',
        fontSize: '14px'
      }}>
        <strong>🎯 Python Tracing Patterns:</strong>
        
        <div style={{ marginTop: '15px' }}>
          <strong style={{ color: '#2196f3' }}>Automatic Span (start_span):</strong>
          <ul style={{ marginTop: '8px', marginLeft: '20px', lineHeight: '1.8', color: '#666' }}>
            <li>Python context manager handles span lifecycle</li>
            <li>Ends automatically when context exits</li>
            <li>Perfect for simple, self-contained operations</li>
            <li>Clean Pythonic syntax</li>
          </ul>
        </div>

        <div style={{ marginTop: '15px' }}>
          <strong style={{ color: '#9c27b0' }}>Manual Span (start_manual_span):</strong>
          <ul style={{ marginTop: '8px', marginLeft: '20px', lineHeight: '1.8', color: '#666' }}>
            <li>Gives you full control over span lifecycle</li>
            <li>Context manager still handles cleanup automatically</li>
            <li>Perfect for tracking multiple steps within one span</li>
            <li>Use when you need to update span attributes throughout the operation</li>
          </ul>
        </div>
      </div>

      {/* API Reference */}
      <div style={{ 
        marginTop: '20px', 
        padding: '15px', 
        backgroundColor: '#e3f2fd',
        borderRadius: '8px',
        fontSize: '14px',
        borderLeft: '4px solid #2196f3'
      }}>
        <strong>💡 Python Span Methods:</strong>
        <ul style={{ marginTop: '10px', marginLeft: '20px', lineHeight: '1.8' }}>
          <li><code>span.set_attribute(key, value)</code> - Add custom metadata to the span</li>
          <li><code>span.set_status_ok()</code> - Mark span as successful</li>
          <li><code>span.set_status_error(message)</code> - Mark span as failed</li>
          <li><code>span.record_exception(error)</code> - Record an error within the span</li>
        </ul>
      </div>
    </div>
  );
}

export default TracesDemo;

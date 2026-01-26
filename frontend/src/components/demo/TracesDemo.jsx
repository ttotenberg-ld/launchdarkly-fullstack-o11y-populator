import { useState } from 'react';
import { LDObserve } from '@launchdarkly/observability';
import { showToast } from '../infrastructure/Toast';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001';

function TracesDemo() {
  const [simpleResult, setSimpleResult] = useState(null);
  const [multiStepResult, setMultiStepResult] = useState(null);
  const [multiStepProgress, setMultiStepProgress] = useState('');

  const handleSimpleDistributedTrace = async () => {
    setSimpleResult('Processing...');
    
    // Create a span that wraps the entire frontend-to-backend request
    await LDObserve.startSpan('frontend.distributed.api.simple', async (span) => {
      span.setAttribute('source', 'frontend');
      span.setAttribute('service', 'react-frontend');
      span.setAttribute('operation.type', 'distributed_trace');
      span.setAttribute('endpoint', '/api/traces/simple');
      
      try {
        // The backend will automatically create child spans
        const response = await fetch(`${API_URL}/api/traces/simple`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
        });
        
        const data = await response.json();
        
        span.setAttribute('http.status_code', response.status);
        span.setAttribute('response.success', data.success);
        
        if (data.success) {
          span.setStatus({ code: 1 }); // SpanStatusCode.OK
          setSimpleResult(`✓ Distributed Trace Complete: ${data.message}`);
        } else {
          span.setStatus({ code: 2, message: 'Backend returned error' }); // SpanStatusCode.ERROR
          setSimpleResult('✗ Backend returned an error');
        }
      } catch (error) {
        console.error('Failed to call backend:', error);
        span.setStatus({ code: 2, message: error.message }); // SpanStatusCode.ERROR
        span.setAttribute('error', true);
        setSimpleResult('✗ Failed to connect to backend');
        showToast('Failed to call backend API. Make sure the backend server is running.', 'error');
      }
    });
  };

  const handleMultiStepDistributedTrace = async () => {
    setMultiStepResult('Processing...');
    setMultiStepProgress('Starting frontend request...');
    
    // Manual span for more control over the distributed trace
    LDObserve.startManualSpan('frontend.distributed.workflow.multi_step', async (span) => {
      try {
        span.setAttribute('source', 'frontend');
        span.setAttribute('service', 'react-frontend');
        span.setAttribute('operation.type', 'distributed_multi_step');
        span.setAttribute('endpoint', '/api/traces/multi-step');
        
        setMultiStepProgress('Calling backend for multi-step workflow...');
        
        // Backend will process multiple steps and create child spans
        const response = await fetch(`${API_URL}/api/traces/multi-step`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
        });
        
        const data = await response.json();
        
        span.setAttribute('http.status_code', response.status);
        span.setAttribute('response.success', data.success);
        span.setAttribute('backend.completed_steps', data.completed_steps);
        
        if (data.success) {
          setMultiStepProgress('Backend processing complete!');
          await new Promise(resolve => setTimeout(resolve, 500));
          
          span.setStatus({ code: 1 }); // SpanStatusCode.OK
          setMultiStepResult(`✓ Distributed Trace Complete: ${data.message}`);
          setMultiStepProgress('');
        } else {
          span.setStatus({ code: 2, message: data.message }); // SpanStatusCode.ERROR
          setMultiStepResult(`✗ ${data.message}`);
          setMultiStepProgress('');
        }
      } catch (error) {
        console.error('Failed to call backend:', error);
        span.setStatus({ code: 2, message: error.message }); // SpanStatusCode.ERROR
        span.setAttribute('error', true);
        
        LDObserve.recordError(error, 'Frontend: Distributed multi-step trace failed', {
          source: 'frontend',
          service: 'react-frontend',
          component: 'TracesDemo.jsx',
        });
        
        setMultiStepResult(`✗ Failed to connect to backend: ${error.message}`);
        setMultiStepProgress('');
        showToast('Failed to call backend API. Make sure the backend server is running.', 'error');
      } finally {
        span.end();
      }
    });
  };

  return (
    <div className="card">
      <h2>🔍 Distributed Traces Demo</h2>
      <p>
        Create <strong>distributed traces</strong> that span from frontend through backend. 
        When you click a button, the frontend creates a trace span around the API call, 
        and the backend automatically continues that trace with child spans. This shows 
        the complete request flow across your entire stack.
      </p>

      {/* Distributed Traces */}
      <div style={{ 
        marginTop: '20px', 
        padding: '20px', 
        backgroundColor: '#e8f5e9', 
        borderRadius: '8px',
        borderLeft: '4px solid #4caf50'
      }}>
        <h3 style={{ marginBottom: '15px', color: '#333' }}>
          🌐 Frontend → Backend Traces
        </h3>

        {/* Simple Distributed Trace */}
        <div style={{ marginBottom: '30px' }}>
          <h4 style={{ marginBottom: '10px', color: '#555' }}>
            Example 1: Simple Distributed Trace
          </h4>
          <p style={{ fontSize: '14px', color: '#666', marginBottom: '15px' }}>
            Frontend creates a span around the API call, backend processes the request with automatic span management.
            The trace shows the full request journey from browser to server.
          </p>
          
          <button onClick={handleSimpleDistributedTrace} style={{ backgroundColor: '#2196f3' }}>
            Run Simple Distributed Trace
          </button>
          
          {simpleResult && (
            <div style={{
              marginTop: '15px',
              padding: '12px',
              backgroundColor: simpleResult.startsWith('✓') ? '#c8e6c9' : '#ffccbc',
              borderRadius: '6px',
              borderLeft: `4px solid ${simpleResult.startsWith('✓') ? '#4caf50' : '#ff5722'}`,
              fontSize: '14px'
            }}>
              {simpleResult}
            </div>
          )}
        </div>

        {/* Multi-Step Distributed Trace */}
        <div>
          <h4 style={{ marginBottom: '10px', color: '#555' }}>
            Example 2: Multi-Step Distributed Trace
          </h4>
          <p style={{ fontSize: '14px', color: '#666', marginBottom: '15px' }}>
            Frontend creates a manual span for detailed control, backend processes multiple steps.
            Perfect for tracking complex workflows across your entire application.
          </p>
          
          <button onClick={handleMultiStepDistributedTrace} style={{ backgroundColor: '#9c27b0' }}>
            Run Multi-Step Distributed Trace
          </button>
          
          {multiStepProgress && (
            <div style={{
              marginTop: '15px',
              padding: '12px',
              backgroundColor: '#e1bee7',
              borderRadius: '6px',
              borderLeft: '4px solid #9c27b0',
              fontSize: '14px',
              fontWeight: '600'
            }}>
              ⏳ {multiStepProgress}
            </div>
          )}
          
          {multiStepResult && !multiStepProgress && (
            <div style={{
              marginTop: '15px',
              padding: '12px',
              backgroundColor: multiStepResult.startsWith('✓') ? '#c8e6c9' : '#ffccbc',
              borderRadius: '6px',
              borderLeft: `4px solid ${multiStepResult.startsWith('✓') ? '#4caf50' : '#ff5722'}`,
              fontSize: '14px'
            }}>
              {multiStepResult}
            </div>
          )}
        </div>
      </div>

      <details style={{ marginTop: '20px', fontSize: '14px' }}>
        <summary style={{ cursor: 'pointer', fontWeight: '600', color: '#555', marginBottom: '10px' }}>
          View Distributed Tracing API Usage & Examples
        </summary>
        
        {/* Distributed Tracing Example */}
        <div style={{ 
          marginTop: '15px', 
          padding: '15px', 
          backgroundColor: '#e8f5e9',
          borderRadius: '8px',
          fontSize: '14px',
          borderLeft: '4px solid #4caf50'
        }}>
          <strong>🌐 Frontend → Backend Distributed Trace:</strong>
          <pre style={{ 
            marginTop: '10px',
            padding: '12px',
            backgroundColor: '#fff',
            borderRadius: '4px',
            border: '1px solid #ddd',
            overflow: 'auto'
          }}>
{`// Frontend creates a span around the API call
await LDObserve.startSpan('distributed.api.request', async (span) => {
  span.setAttribute('source', 'frontend');
  span.setAttribute('service', 'react-frontend');
  span.setAttribute('endpoint', '/api/data');
  
  // Make API call - trace context is automatically propagated
  const response = await fetch(\`\${API_URL}/api/data\`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  });
  
  span.setAttribute('http.status_code', response.status);
  const data = await response.json();
  
  span.setStatus({ code: 1 }); // OK (UNSET=0, OK=1, ERROR=2)
});`}
          </pre>
        </div>

        {/* Backend Example */}
        <div style={{ 
          marginTop: '15px', 
          padding: '15px', 
          backgroundColor: '#f3e5f5',
          borderRadius: '8px',
          fontSize: '14px',
          borderLeft: '4px solid #9c27b0'
        }}>
          <strong>🔧 Backend Receives and Continues the Trace:</strong>
          <pre style={{ 
            marginTop: '10px',
            padding: '12px',
            backgroundColor: '#fff',
            borderRadius: '4px',
            border: '1px solid #ddd',
            overflow: 'auto'
          }}>
{`# Backend automatically continues the trace from frontend
from ldobserve.observe import start_span

@app.route('/api/data', methods=['POST'])
def handle_data():
    # Trace context is automatically extracted from request headers
    with start_span('backend.process.data') as span:
        span.set_attribute('source', 'backend')
        span.set_attribute('service', 'python-backend')
        
        # Process data - this becomes a child span of frontend span
        result = process_data()
        
        span.set_attribute('result.status', 'success')
        return jsonify(result)`}
          </pre>
        </div>

        <div style={{ 
          marginTop: '15px', 
          padding: '15px', 
          backgroundColor: '#e3f2fd',
          borderRadius: '8px',
          fontSize: '14px',
          borderLeft: '4px solid #2196f3'
        }}>
          <strong>💡 Key Concepts:</strong>
          <ul style={{ marginTop: '10px', marginLeft: '20px', lineHeight: '1.8' }}>
            <li><strong>Distributed Tracing:</strong> A single trace spans from frontend through backend, showing the complete request flow</li>
            <li><strong>Automatic Context Propagation:</strong> Trace context is automatically passed via HTTP headers (W3C Trace Context standard)</li>
            <li><strong>Parent-Child Spans:</strong> Backend spans become children of the frontend span, creating a trace hierarchy</li>
            <li><strong>Source Attribution:</strong> Each span includes <code>source</code> attribute ('frontend' or 'backend') for filtering</li>
            <li><strong>Service Identification:</strong> <code>service</code> attribute helps identify which service created each span</li>
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
          <strong>📊 What You'll See in LaunchDarkly:</strong>
          <ul style={{ marginTop: '10px', marginLeft: '20px', lineHeight: '1.8' }}>
            <li>A single trace ID shared across frontend and backend spans</li>
            <li>Frontend span as the root/parent span</li>
            <li>Backend spans as child spans nested under the frontend span</li>
            <li>Total duration showing end-to-end request time</li>
            <li>Ability to filter by <code>source</code> or <code>service</code> attributes</li>
          </ul>
        </div>
      </details>
    </div>
  );
}

export default TracesDemo;

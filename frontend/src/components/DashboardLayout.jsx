import { withLDConsumer } from "launchdarkly-react-client-sdk";
import ErrorBoundary from './ErrorBoundary';
import ErrorDemo from './ErrorDemo';
import LogsDemo from './LogsDemo';
import TracesDemo from './TracesDemo';
import FancyWidget from './FancyWidget';

function DashboardLayout( { flags } ) {
  // Debug: Log flags to console
  console.log('Available flags:', flags);
  console.log('releaseFancyWidget flag value:', flags.releaseFancyWidget);

  return (
    <div>
      <header style={{
        textAlign: 'center',
        color: 'white',
        marginBottom: '40px'
      }}>
        <h1 style={{ fontSize: '48px', marginBottom: '10px' }}>
          🚀 LaunchDarkly Observability Demo
        </h1>
        <p style={{ fontSize: '20px', opacity: 0.9 }}>
          Demonstrating Errors, Logs, and Traces
        </p>
      </header>

      <div className="card" style={{ marginBottom: '30px' }}>
        <h2>📊 Observability Features Active</h2>
        <ul style={{ 
          listStyle: 'none', 
          padding: 0,
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
          gap: '15px'
        }}>
          <li style={{ 
            padding: '15px', 
            backgroundColor: '#e8f5e9', 
            borderRadius: '8px',
            borderLeft: '4px solid #4caf50'
          }}>
            <strong>✅ Error Tracking</strong>
            <p style={{ fontSize: '14px', marginTop: '5px', color: '#666' }}>
              Automatic & manual error capture with context
            </p>
          </li>
          <li style={{ 
            padding: '15px', 
            backgroundColor: '#e3f2fd', 
            borderRadius: '8px',
            borderLeft: '4px solid #2196f3'
          }}>
            <strong>✅ Custom Logs</strong>
            <p style={{ fontSize: '14px', marginTop: '5px', color: '#666' }}>
              Recording custom log events with metadata
            </p>
          </li>
          <li style={{ 
            padding: '15px', 
            backgroundColor: '#f3e5f5', 
            borderRadius: '8px',
            borderLeft: '4px solid #9c27b0'
          }}>
            <strong>✅ Distributed Tracing</strong>
            <p style={{ fontSize: '14px', marginTop: '5px', color: '#666' }}>
              Trace spans for sync & async operations
            </p>
          </li>
        </ul>
      </div>

      <ErrorDemo />
      <LogsDemo />
      <TracesDemo />

      {/* Debug: Flag Status Indicator */}
      <div className="card" style={{ 
        backgroundColor: flags.releaseFancyWidget ? '#e8f5e9' : '#ffebee',
        borderLeft: flags.releaseFancyWidget ? '4px solid #4caf50' : '4px solid #f44336',
        marginBottom: '30px'
      }}>
        <h3>🎛️ Feature Flag Status</h3>
        <p style={{ fontSize: '16px', marginTop: '10px' }}>
          <strong>Flag Key:</strong> <code style={{ 
            background: 'rgba(0,0,0,0.05)', 
            padding: '2px 6px', 
            borderRadius: '3px',
            fontFamily: 'monospace' 
          }}>releaseFancyWidget</code>
        </p>
        <p style={{ fontSize: '16px', marginTop: '5px' }}>
          <strong>Status:</strong> <span style={{ 
            fontWeight: 'bold',
            color: flags.releaseFancyWidget ? '#4caf50' : '#f44336'
          }}>
            {flags.releaseFancyWidget ? '✅ ON' : '❌ OFF'}
          </span>
        </p>
        <p style={{ fontSize: '14px', marginTop: '10px', color: '#666' }}>
          {flags.releaseFancyWidget 
            ? 'The Fancy Widget should be visible below!' 
            : 'Toggle this flag ON in your LaunchDarkly dashboard to see the Fancy Widget.'}
        </p>
      </div>

      {flags.releaseFancyWidget && (
        <ErrorBoundary>
          <FancyWidget />
        </ErrorBoundary>
      )}

      <div className="card" style={{ 
        backgroundColor: '#f8f9fa',
        borderLeft: '4px solid #667eea'
      }}>
        <h2>📚 Next Steps</h2>
        <ol style={{ lineHeight: '2', color: '#333' }}>
          <li>Interact with the demo components above to generate observability data</li>
          <li>Check your LaunchDarkly dashboard under <strong>Monitor</strong></li>
          <li>View captured errors with stack traces and context</li>
          <li>Review custom logs and their associated metadata</li>
          <li>Analyze trace spans to understand operation timing and flow</li>
        </ol>
      </div>
    </div>
  );
}

export default withLDConsumer()(DashboardLayout);


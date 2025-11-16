import React from 'react';
import { LDObserve } from '@launchdarkly/observability';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { 
      hasError: false, 
      error: null,
      errorInfo: null 
    };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    // Log error details
    console.error('Error caught by boundary:', error, errorInfo);
    
    // Forward error to LaunchDarkly Observability
    LDObserve.recordError(
      error,
      'React Error Boundary',
      { componentStack: errorInfo.componentStack }
    );

    // Store error details in state
    this.setState({
      error,
      errorInfo
    });
  }

  handleReset = () => {
    this.setState({ 
      hasError: false, 
      error: null,
      errorInfo: null 
    });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          padding: '40px',
          maxWidth: '800px',
          margin: '0 auto',
          textAlign: 'center'
        }}>
          <div className="card" style={{ 
            backgroundColor: '#fff3cd', 
            borderLeft: '4px solid #ffc107' 
          }}>
            <h1 style={{ color: '#856404', marginBottom: '20px' }}>
              ⚠️ Something went wrong
            </h1>
            <p style={{ color: '#856404', fontSize: '16px', marginBottom: '20px' }}>
              An error has been caught and reported to LaunchDarkly Observability.
            </p>
            
            {this.state.error && (
              <div style={{
                backgroundColor: '#fff',
                padding: '20px',
                borderRadius: '8px',
                marginBottom: '20px',
                textAlign: 'left'
              }}>
                <h3 style={{ color: '#d9534f', marginBottom: '10px' }}>Error Details:</h3>
                <code style={{ 
                  display: 'block',
                  padding: '10px',
                  backgroundColor: '#f8f9fa',
                  borderRadius: '4px',
                  color: '#d9534f',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word'
                }}>
                  {this.state.error.toString()}
                </code>
                
                {this.state.errorInfo && this.state.errorInfo.componentStack && (
                  <details style={{ marginTop: '15px' }}>
                    <summary style={{ 
                      cursor: 'pointer', 
                      color: '#666',
                      fontWeight: 'bold',
                      marginBottom: '10px'
                    }}>
                      Component Stack Trace
                    </summary>
                    <code style={{ 
                      display: 'block',
                      padding: '10px',
                      backgroundColor: '#f8f9fa',
                      borderRadius: '4px',
                      fontSize: '12px',
                      color: '#333',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                      maxHeight: '300px',
                      overflow: 'auto'
                    }}>
                      {this.state.errorInfo.componentStack}
                    </code>
                  </details>
                )}
              </div>
            )}
            
            <button 
              onClick={this.handleReset}
              style={{
                backgroundColor: '#ffc107',
                color: '#856404',
                fontWeight: 'bold'
              }}
            >
              Reset and Try Again
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;


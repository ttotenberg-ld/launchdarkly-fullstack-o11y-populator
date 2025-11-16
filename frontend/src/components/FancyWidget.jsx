function FancyWidget() {
  return (
    <div className="card" style={{
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      color: 'white',
      borderLeft: 'none',
      padding: '25px'
    }}>
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        gap: '15px',
        marginBottom: '15px'
      }}>
        <div style={{ fontSize: '32px' }}>✨</div>
        <h3 style={{ 
          fontSize: '24px', 
          margin: 0
        }}>
          Fancy Widget
        </h3>
      </div>
      
      <p style={{ 
        fontSize: '16px', 
        lineHeight: '1.5',
        margin: '0 0 15px 0',
        color: 'white'
      }}>
        This widget is controlled by the <code style={{
          background: 'rgba(255, 255, 255, 0.3)',
          padding: '3px 8px',
          borderRadius: '4px',
          fontFamily: 'monospace',
          fontSize: '14px',
          fontWeight: '600'
        }}>releaseFancyWidget</code> feature flag.
      </p>

      <p style={{ 
        fontSize: '14px',
        fontStyle: 'italic',
        margin: 0,
        color: 'rgba(255, 255, 255, 0.95)'
      }}>
        Toggle the flag in your LaunchDarkly dashboard to make this component appear or disappear!
      </p>
    </div>
  );
}

export default FancyWidget;


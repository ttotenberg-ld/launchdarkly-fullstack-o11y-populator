import React from 'react';

const SimulationControls = ({ 
  isPlaying, 
  onToggle, 
  rate, 
  onRateChange,
  currentAction,
  stats
}) => {
  return (
    <div className="simulation-controls">
      <div className="simulation-header">
        <div className="simulation-title">Traffic Simulation</div>
        <div className="simulation-actions">
          <button 
            onClick={onToggle}
            className={isPlaying ? 'danger' : 'success'}
          >
            {isPlaying ? 'Stop Simulation' : 'Start Simulation'}
          </button>
        </div>
      </div>

      {isPlaying && currentAction && (
        <div className="current-action">
          <div className="action-indicator" />
          <div className="action-text">
            {currentAction.scenario} - {currentAction.user?.email || 'Unknown user'}
          </div>
        </div>
      )}

      <div className="rate-slider">
        <span className="rate-label">Request rate:</span>
        <input 
          type="range" 
          min="1" 
          max="60" 
          value={rate}
          onChange={(e) => onRateChange(parseInt(e.target.value))}
        />
        <span style={{ minWidth: '80px', textAlign: 'right' }}>{rate} req/min</span>
      </div>

      {stats && (
        <div style={{ 
          display: 'flex', 
          gap: '24px', 
          marginTop: '16px',
          fontSize: '14px',
          color: 'var(--ld-gray-600)'
        }}>
          <span>Sessions: <strong>{stats.sessions || 0}</strong></span>
          <span>Success: <strong style={{ color: 'var(--ld-green)' }}>{stats.success || 0}</strong></span>
          <span>Errors: <strong style={{ color: 'var(--ld-red)' }}>{stats.errors || 0}</strong></span>
        </div>
      )}
    </div>
  );
};

export default SimulationControls;

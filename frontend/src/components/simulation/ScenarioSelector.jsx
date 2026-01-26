import React from 'react';

const ScenarioSelector = ({ scenarios, activeScenarios, onToggle }) => {
  const defaultScenarios = [
    { id: 'browse_products', name: 'Browse Products', description: 'User browses and views products', weight: 35 },
    { id: 'user_login', name: 'User Login', description: 'Login and view profile', weight: 20 },
    { id: 'checkout_flow', name: 'Checkout Flow', description: 'Full checkout with payment', weight: 15 },
    { id: 'search_products', name: 'Search Products', description: 'Search and filter products', weight: 15 },
    { id: 'update_profile', name: 'Update Profile', description: 'Update user preferences', weight: 10 },
    { id: 'view_dashboard', name: 'View Dashboard', description: 'Load dashboard metrics', weight: 5 },
  ];

  const scenarioList = scenarios || defaultScenarios;
  const active = activeScenarios || scenarioList.map(s => s.id);

  return (
    <div className="card">
      <div className="card-header">
        <h3 className="card-title">Traffic Scenarios</h3>
        <span className="badge info">{active.length} Active</span>
      </div>
      <div className="card-body">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
          {scenarioList.map((scenario) => (
            <div 
              key={scenario.id}
              className={`scenario-card ${active.includes(scenario.id) ? 'active' : ''}`}
              onClick={() => onToggle && onToggle(scenario.id)}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div className="scenario-name">{scenario.name}</div>
                <span className="badge info">{scenario.weight}%</span>
              </div>
              <div className="scenario-description">{scenario.description}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default ScenarioSelector;

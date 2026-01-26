import React, { useState, useEffect } from 'react';
import { withLDConsumer } from 'launchdarkly-react-client-sdk';
import Sidebar from '../layout/Sidebar';
import Header from '../layout/Header';
import MetricsCards from '../dashboard/MetricsCards';
import ServiceHealth from '../dashboard/ServiceHealth';
import ActivityFeed from '../dashboard/ActivityFeed';
import SimulationControls from '../simulation/SimulationControls';
import ScenarioSelector from '../simulation/ScenarioSelector';
import { useAutoPlay } from '../../hooks/useAutoPlay';
import { getRandomUser } from '../../services/api';

// Demo sections
import ErrorDemo from '../demo/ErrorDemo';
import LogsDemo from '../demo/LogsDemo';
import TracesDemo from '../demo/TracesDemo';

const DashboardLayout = ({ flags }) => {
  const [activeSection, setActiveSection] = useState('dashboard');
  const [currentUser] = useState(getRandomUser());
  
  const { 
    isPlaying, 
    rate, 
    setRate, 
    currentAction, 
    stats, 
    activities,
    toggle 
  } = useAutoPlay();

  // Calculate metrics from stats
  const metrics = {
    activeSessions: stats.sessions,
    tracesToday: stats.sessions * 3, // Approximate traces per session
    errorRate: stats.sessions > 0 ? (stats.errors / stats.sessions) * 100 : 0,
    avgResponseTime: 245 + Math.floor(Math.random() * 50),
  };

  const sectionTitles = {
    dashboard: 'Dashboard',
    traces: 'Traces',
    errors: 'Errors',
    logs: 'Logs',
    services: 'Service Health',
    simulation: 'Traffic Simulation',
  };

  const renderContent = () => {
    switch (activeSection) {
      case 'dashboard':
        return (
          <>
            <SimulationControls
              isPlaying={isPlaying}
              onToggle={toggle}
              rate={rate}
              onRateChange={setRate}
              currentAction={currentAction}
              stats={stats}
            />
            <MetricsCards stats={metrics} />
            <div className="grid-2">
              <ServiceHealth />
              <ActivityFeed activities={activities} />
            </div>
          </>
        );
      
      case 'traces':
        return (
          <>
            <SimulationControls
              isPlaying={isPlaying}
              onToggle={toggle}
              rate={rate}
              onRateChange={setRate}
              currentAction={currentAction}
              stats={stats}
            />
            <TracesDemo />
          </>
        );
      
      case 'errors':
        return (
          <>
            <SimulationControls
              isPlaying={isPlaying}
              onToggle={toggle}
              rate={rate}
              onRateChange={setRate}
              currentAction={currentAction}
              stats={stats}
            />
            <ErrorDemo />
          </>
        );
      
      case 'logs':
        return (
          <>
            <SimulationControls
              isPlaying={isPlaying}
              onToggle={toggle}
              rate={rate}
              onRateChange={setRate}
              currentAction={currentAction}
              stats={stats}
            />
            <LogsDemo />
          </>
        );
      
      case 'services':
        return (
          <>
            <div className="card" style={{ marginBottom: '24px' }}>
              <div className="card-header">
                <h3 className="card-title">Architecture Overview</h3>
              </div>
              <div className="card-body">
                <p style={{ color: 'var(--ld-gray-600)', marginBottom: '16px' }}>
                  This demo runs 9 Flask microservices that communicate via HTTP with distributed tracing.
                  Each service is instrumented with LaunchDarkly Observability for full end-to-end visibility.
                </p>
                <div style={{ 
                  background: 'var(--ld-gray-100)', 
                  borderRadius: '8px', 
                  padding: '16px',
                  fontFamily: 'monospace',
                  fontSize: '13px',
                  lineHeight: '1.8'
                }}>
                  Frontend → API Gateway → Auth/User/Order/Search Services<br/>
                  Order Service → Payment Service → Notification Service<br/>
                  Order Service → Inventory Service → Notification Service
                </div>
              </div>
            </div>
            <ServiceHealth />
          </>
        );
      
      case 'simulation':
        return (
          <>
            <SimulationControls
              isPlaying={isPlaying}
              onToggle={toggle}
              rate={rate}
              onRateChange={setRate}
              currentAction={currentAction}
              stats={stats}
            />
            <ScenarioSelector />
            <div className="card" style={{ marginTop: '24px' }}>
              <div className="card-header">
                <h3 className="card-title">Recent Sessions</h3>
              </div>
              <div className="card-body">
                <ActivityFeed activities={activities} />
              </div>
            </div>
          </>
        );
      
      default:
        return null;
    }
  };

  return (
    <>
      <Sidebar 
        activeSection={activeSection} 
        onSectionChange={setActiveSection}
      />
      <main className="main-content">
        <Header 
          title={sectionTitles[activeSection]}
          user={currentUser}
          isAutoPlaying={isPlaying}
          onAutoPlayToggle={toggle}
        />
        <div className="content">
          {renderContent()}
          
          {flags?.releaseFancyWidget && (
            <div className="card" style={{ marginTop: '24px' }}>
              <div className="card-header">
                <h3 className="card-title">Feature Flag Demo</h3>
                <span className="badge success">Flag Enabled</span>
              </div>
              <div className="card-body">
                <p style={{ color: 'var(--ld-gray-600)' }}>
                  The <code>releaseFancyWidget</code> feature flag is currently <strong>enabled</strong>.
                  This section is only visible when the flag is on.
                </p>
              </div>
            </div>
          )}
        </div>
      </main>
    </>
  );
};

export default withLDConsumer()(DashboardLayout);

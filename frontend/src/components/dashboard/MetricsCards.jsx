import React from 'react';

const MetricsCards = ({ stats }) => {
  const metrics = [
    {
      label: 'Active Sessions',
      value: stats?.activeSessions || 0,
      change: '+12%',
      positive: true,
    },
    {
      label: 'Traces Today',
      value: stats?.tracesToday || 0,
      change: '+8%',
      positive: true,
    },
    {
      label: 'Error Rate',
      value: `${(stats?.errorRate || 0).toFixed(1)}%`,
      change: '-2.3%',
      positive: true,
    },
    {
      label: 'Avg Response Time',
      value: `${stats?.avgResponseTime || 0}ms`,
      change: '+5ms',
      positive: false,
    },
  ];

  return (
    <div className="metrics-grid">
      {metrics.map((metric, index) => (
        <div key={index} className="metric-card">
          <div className="metric-label">{metric.label}</div>
          <div className="metric-value">{metric.value}</div>
          <div className={`metric-change ${metric.positive ? 'positive' : 'negative'}`}>
            {metric.change} from yesterday
          </div>
        </div>
      ))}
    </div>
  );
};

export default MetricsCards;

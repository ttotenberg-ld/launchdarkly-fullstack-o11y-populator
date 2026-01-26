import React from 'react';

const ServiceHealth = ({ services }) => {
  const defaultServices = [
    { name: 'api-gateway', port: 5000, status: 'healthy' },
    { name: 'auth-service', port: 5001, status: 'healthy' },
    { name: 'user-service', port: 5002, status: 'healthy' },
    { name: 'order-service', port: 5003, status: 'healthy' },
    { name: 'payment-service', port: 5004, status: 'degraded' },
    { name: 'inventory-service', port: 5005, status: 'healthy' },
    { name: 'notification-service', port: 5006, status: 'healthy' },
    { name: 'analytics-service', port: 5007, status: 'healthy' },
    { name: 'search-service', port: 5008, status: 'healthy' },
  ];

  const serviceList = services || defaultServices;

  return (
    <div className="card">
      <div className="card-header">
        <h3 className="card-title">Service Health</h3>
        <span className="badge success">
          {serviceList.filter(s => s.status === 'healthy').length}/{serviceList.length} Healthy
        </span>
      </div>
      <div className="card-body">
        <div className="services-grid">
          {serviceList.map((service) => (
            <div key={service.name} className="service-card">
              <div className={`service-status ${service.status}`} />
              <div className="service-info">
                <div className="service-name">{service.name}</div>
                <div className="service-port">:{service.port}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default ServiceHealth;

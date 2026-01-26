import React from 'react';

const ActivityFeed = ({ activities }) => {
  const defaultActivities = [
    { 
      id: 1, 
      type: 'success', 
      title: 'Checkout completed', 
      meta: 'luna@staylightly.io - 2s ago',
      icon: 'check'
    },
    { 
      id: 2, 
      type: 'error', 
      title: 'Payment declined', 
      meta: 'lance@darklaunchly.com - 15s ago',
      icon: 'x'
    },
    { 
      id: 3, 
      type: 'info', 
      title: 'User login', 
      meta: 'darcy@lunchdarkly.net - 23s ago',
      icon: 'user'
    },
    { 
      id: 4, 
      type: 'success', 
      title: 'Search query', 
      meta: 'larry@launchdorkly.io - 31s ago',
      icon: 'search'
    },
    { 
      id: 5, 
      type: 'info', 
      title: 'Profile updated', 
      meta: 'lydia@dimlylaunch.com - 45s ago',
      icon: 'edit'
    },
    { 
      id: 6, 
      type: 'error', 
      title: 'Inventory reservation failed', 
      meta: 'drake@launchbrightly.io - 52s ago',
      icon: 'x'
    },
    { 
      id: 7, 
      type: 'success', 
      title: 'Order placed', 
      meta: 'dawn@toggledarkly.com - 1m ago',
      icon: 'check'
    },
  ];

  const activityList = activities || defaultActivities;

  const getIcon = (type) => {
    const icons = {
      check: (
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="20 6 9 17 4 12"></polyline>
        </svg>
      ),
      x: (
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      ),
      user: (
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
          <circle cx="12" cy="7" r="4"></circle>
        </svg>
      ),
      search: (
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="11" cy="11" r="8"></circle>
          <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
        </svg>
      ),
      edit: (
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
        </svg>
      ),
    };
    return icons[type] || icons.check;
  };

  return (
    <div className="card">
      <div className="card-header">
        <h3 className="card-title">Recent Activity</h3>
      </div>
      <div className="card-body">
        <div className="activity-feed">
          {activityList.map((activity) => (
            <div key={activity.id} className="activity-item">
              <div className={`activity-icon ${activity.type}`}>
                {getIcon(activity.icon)}
              </div>
              <div className="activity-content">
                <div className="activity-title">{activity.title}</div>
                <div className="activity-meta">{activity.meta}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default ActivityFeed;

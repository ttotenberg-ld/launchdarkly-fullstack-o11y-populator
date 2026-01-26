import { useState, useEffect } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';

export default function Account() {
  const { user, isAuthenticated } = useAuth();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadOrders() {
      if (!user) return;
      try {
        const result = await api.listOrders();
        if (result.success && result.data.orders) {
          setOrders(result.data.orders);
        }
      } catch (err) {
        console.error('Failed to load orders:', err);
      } finally {
        setLoading(false);
      }
    }
    loadOrders();
  }, [user]);

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: { pathname: '/account' } }} replace />;
  }

  return (
    <div className="account-page" data-testid="account-page">
      <div className="account-header">
        <div className="account-avatar">
          {user?.name?.charAt(0) || 'U'}
        </div>
        <div className="account-info">
          <h1>{user?.name || 'User'}</h1>
          <p>{user?.email}</p>
        </div>
        <Link to="/account/settings" className="btn-secondary" data-testid="settings-link">
          Settings
        </Link>
      </div>

      <div className="account-content">
        <section className="account-section">
          <h2>Recent Orders</h2>
          
          {loading ? (
            <div className="loading-orders">Loading orders...</div>
          ) : orders.length > 0 ? (
            <div className="orders-list" data-testid="orders-list">
              {orders.map(order => (
                <div key={order.id} className="order-card" data-testid="order-item">
                  <div className="order-header">
                    <span className="order-id">Order #{order.id}</span>
                    <span className={`order-status ${order.status}`}>
                      {order.status || 'Completed'}
                    </span>
                  </div>
                  <div className="order-details">
                    <span className="order-date">
                      {new Date(order.date || Date.now()).toLocaleDateString()}
                    </span>
                    <span className="order-total">
                      ${order.total?.toFixed(2) || '0.00'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-orders" data-testid="no-orders">
              <p>You haven't placed any orders yet.</p>
              <Link to="/products" className="btn-primary">Start Shopping</Link>
            </div>
          )}
        </section>

        <section className="account-section">
          <h2>Account Details</h2>
          <div className="details-grid">
            <div className="detail-card">
              <h3>Contact Information</h3>
              <p><strong>Email:</strong> {user?.email}</p>
              <p><strong>Member since:</strong> 2024</p>
            </div>
            <div className="detail-card">
              <h3>Preferences</h3>
              <p><strong>Newsletter:</strong> Subscribed</p>
              <p><strong>Notifications:</strong> Enabled</p>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

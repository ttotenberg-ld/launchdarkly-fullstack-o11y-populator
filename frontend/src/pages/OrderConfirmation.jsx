import { useLocation, Link, Navigate } from 'react-router-dom';

export default function OrderConfirmation() {
  const location = useLocation();
  const { orderId, total } = location.state || {};

  if (!orderId) {
    return <Navigate to="/" replace />;
  }

  return (
    <div className="order-confirmation-page" data-testid="order-confirmation">
      <div className="confirmation-content">
        <div className="confirmation-icon">
          <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
            <polyline points="22 4 12 14.01 9 11.01"></polyline>
          </svg>
        </div>
        
        <h1>Order Confirmed!</h1>
        <p className="confirmation-message">
          Thank you for your purchase. Your order has been successfully placed.
        </p>
        
        <div className="order-details">
          <div className="detail-row">
            <span>Order Number:</span>
            <span className="order-id" data-testid="order-id">{orderId}</span>
          </div>
          {total && (
            <div className="detail-row">
              <span>Total Charged:</span>
              <span data-testid="order-total">${total.toFixed(2)}</span>
            </div>
          )}
        </div>

        <p className="confirmation-note">
          A confirmation email has been sent to your email address.
        </p>

        <div className="confirmation-actions">
          <Link to="/account" className="btn-secondary" data-testid="view-orders">
            View My Orders
          </Link>
          <Link to="/products" className="btn-primary" data-testid="continue-shopping">
            Continue Shopping
          </Link>
        </div>
      </div>
    </div>
  );
}

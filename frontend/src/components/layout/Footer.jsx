import { Link } from 'react-router-dom';

export default function Footer() {
  return (
    <footer className="footer" data-testid="footer">
      <div className="footer-container">
        <div className="footer-section">
          <h4>LD Store</h4>
          <p>Your one-stop shop for feature flags and progressive rollouts.</p>
        </div>
        
        <div className="footer-section">
          <h4>Quick Links</h4>
          <ul>
            <li><Link to="/products">Products</Link></li>
            <li><Link to="/cart">Cart</Link></li>
            <li><Link to="/account">Account</Link></li>
          </ul>
        </div>
        
        <div className="footer-section">
          <h4>Support</h4>
          <ul>
            <li><a href="#">Help Center</a></li>
            <li><a href="#">Contact Us</a></li>
            <li><a href="#">Shipping Info</a></li>
          </ul>
        </div>
        
        <div className="footer-section">
          <h4>Connect</h4>
          <p>Powered by LaunchDarkly Observability</p>
        </div>
      </div>
      
      <div className="footer-bottom">
        <p>&copy; 2024 LD Store. Demo Application.</p>
      </div>
    </footer>
  );
}

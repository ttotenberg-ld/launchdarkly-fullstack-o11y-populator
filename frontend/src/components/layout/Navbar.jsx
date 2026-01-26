import { Link, useNavigate } from 'react-router-dom';
import { useCart } from '../../context/CartContext';
import { useAuth } from '../../context/AuthContext';
import SearchBar from '../products/SearchBar';

export default function Navbar() {
  const { cartItems } = useCart();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  
  const cartCount = cartItems.reduce((sum, item) => sum + item.quantity, 0);

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <nav className="navbar" data-testid="navbar">
      <div className="navbar-container">
        <Link to="/" className="navbar-logo" data-testid="logo">
          <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" width="32" height="32">
            <rect width="32" height="32" rx="8" fill="#6c5ce7"/>
            <path d="M8 16L14 10L20 16L14 22L8 16Z" fill="white"/>
            <path d="M14 16L20 10L26 16L20 22L14 16Z" fill="white" fillOpacity="0.6"/>
          </svg>
          <span>LD Store</span>
        </Link>

        <div className="navbar-search">
          <SearchBar />
        </div>

        <div className="navbar-actions">
          <Link to="/products" className="nav-link" data-testid="products-link">
            Products
          </Link>
          
          <Link to="/cart" className="cart-link" data-testid="cart-icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="9" cy="21" r="1"></circle>
              <circle cx="20" cy="21" r="1"></circle>
              <path d="m1 1 4 4 2.68 11.41a2 2 0 0 0 2 1.59h9.72a2 2 0 0 0 2-1.6L23 6H6"></path>
            </svg>
            {cartCount > 0 && (
              <span className="cart-badge" data-testid="cart-count">{cartCount}</span>
            )}
          </Link>

          {user ? (
            <div className="user-menu">
              <Link to="/account" className="nav-link" data-testid="account-link">
                {user.name}
              </Link>
              <button onClick={handleLogout} className="btn-secondary btn-sm" data-testid="logout-button">
                Logout
              </button>
            </div>
          ) : (
            <Link to="/login" className="btn-primary btn-sm" data-testid="login-link">
              Login
            </Link>
          )}
        </div>
      </div>
    </nav>
  );
}

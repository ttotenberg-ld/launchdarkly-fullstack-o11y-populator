import { useState } from 'react';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  
  const { login, loading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  
  const from = location.state?.from?.pathname || '/account';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    if (!email || !password) {
      setError('Please fill in all fields');
      return;
    }

    const result = await login(email, password);
    if (result.success) {
      navigate(from, { replace: true });
    } else {
      setError(result.error || 'Login failed. Please try again.');
    }
  };

  // Demo users for quick login
  const demoUsers = [
    { email: 'luna@staylightly.io', name: 'Luna Darksworth' },
    { email: 'lance@darklaunchly.com', name: 'Lance Dimly' },
    { email: 'darcy@lunchdarkly.net', name: 'Darcy Launch' },
  ];

  const handleDemoLogin = async (demoEmail) => {
    setEmail(demoEmail);
    setPassword('demo123');
    const result = await login(demoEmail, 'demo123');
    if (result.success) {
      navigate(from, { replace: true });
    }
  };

  return (
    <div className="login-page" data-testid="login-page">
      <div className="login-container">
        <div className="login-header">
          <h1>Welcome Back</h1>
          <p>Sign in to your account</p>
        </div>

        {error && (
          <div className="form-error" data-testid="login-error">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="login-form" data-testid="login-form">
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              data-testid="email-input"
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              data-testid="password-input"
              disabled={loading}
            />
          </div>

          <button 
            type="submit" 
            className="btn-primary btn-full"
            disabled={loading}
            data-testid="login-button"
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <div className="login-divider">
          <span>or try a demo account</span>
        </div>

        <div className="demo-users">
          {demoUsers.map(user => (
            <button
              key={user.email}
              className="demo-user-btn"
              onClick={() => handleDemoLogin(user.email)}
              disabled={loading}
              data-testid={`demo-login-${user.email}`}
            >
              <span className="demo-user-avatar">{user.name.charAt(0)}</span>
              <span className="demo-user-info">
                <span className="demo-user-name">{user.name}</span>
                <span className="demo-user-email">{user.email}</span>
              </span>
            </button>
          ))}
        </div>

        <p className="login-footer">
          Don't have an account? <Link to="/login">Sign up</Link>
        </p>
      </div>
    </div>
  );
}

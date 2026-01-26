import { useState } from 'react';
import { Navigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';

export default function Settings() {
  const { user, isAuthenticated } = useAuth();
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [formData, setFormData] = useState({
    name: user?.name || '',
    email: user?.email || '',
    theme: 'light',
    notifications: true,
    newsletter: true,
    language: 'en',
  });

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: { pathname: '/account/settings' } }} replace />;
  }

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    
    try {
      await api.updateUser(user.key, {
        preferences: {
          theme: formData.theme,
          notifications: formData.notifications,
          newsletter: formData.newsletter,
          language: formData.language,
        }
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      console.error('Failed to save settings:', err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="settings-page" data-testid="settings-page">
      <div className="settings-header">
        <Link to="/account" className="back-link">
          ← Back to Account
        </Link>
        <h1>Account Settings</h1>
      </div>

      <form onSubmit={handleSubmit} className="settings-form" data-testid="settings-form">
        <section className="settings-section">
          <h2>Profile Information</h2>
          
          <div className="form-group">
            <label htmlFor="name">Name</label>
            <input
              type="text"
              id="name"
              name="name"
              value={formData.name}
              onChange={handleChange}
              data-testid="name-input"
            />
          </div>

          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              type="email"
              id="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              disabled
              data-testid="email-input"
            />
            <p className="form-hint">Email cannot be changed</p>
          </div>
        </section>

        <section className="settings-section">
          <h2>Preferences</h2>
          
          <div className="form-group">
            <label htmlFor="theme">Theme</label>
            <select
              id="theme"
              name="theme"
              value={formData.theme}
              onChange={handleChange}
              data-testid="theme-select"
            >
              <option value="light">Light</option>
              <option value="dark">Dark</option>
              <option value="auto">System Default</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="language">Language</label>
            <select
              id="language"
              name="language"
              value={formData.language}
              onChange={handleChange}
              data-testid="language-select"
            >
              <option value="en">English</option>
              <option value="es">Spanish</option>
              <option value="fr">French</option>
              <option value="de">German</option>
            </select>
          </div>
        </section>

        <section className="settings-section">
          <h2>Notifications</h2>
          
          <div className="form-group checkbox">
            <input
              type="checkbox"
              id="notifications"
              name="notifications"
              checked={formData.notifications}
              onChange={handleChange}
              data-testid="notifications-checkbox"
            />
            <label htmlFor="notifications">
              Enable push notifications
            </label>
          </div>

          <div className="form-group checkbox">
            <input
              type="checkbox"
              id="newsletter"
              name="newsletter"
              checked={formData.newsletter}
              onChange={handleChange}
              data-testid="newsletter-checkbox"
            />
            <label htmlFor="newsletter">
              Subscribe to newsletter
            </label>
          </div>
        </section>

        <div className="settings-actions">
          <button 
            type="submit" 
            className="btn-primary"
            disabled={saving}
            data-testid="save-settings"
          >
            {saving ? 'Saving...' : saved ? 'Saved!' : 'Save Changes'}
          </button>
        </div>
      </form>
    </div>
  );
}

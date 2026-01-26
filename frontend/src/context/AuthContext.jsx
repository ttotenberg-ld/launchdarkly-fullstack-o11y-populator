import { createContext, useContext, useState, useEffect } from 'react';
import { useLDClient } from 'launchdarkly-react-client-sdk';
import { api } from '../services/api';

const AuthContext = createContext(null);

const AUTH_STORAGE_KEY = 'ld-store-user';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const stored = localStorage.getItem(AUTH_STORAGE_KEY);
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const ldClient = useLDClient();

  useEffect(() => {
    if (user) {
      localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(user));
      // Update LaunchDarkly context with user info
      if (ldClient) {
        ldClient.identify({
          kind: 'user',
          key: user.key,
          name: user.name,
          email: user.email,
        });
      }
    } else {
      localStorage.removeItem(AUTH_STORAGE_KEY);
    }
  }, [user, ldClient]);

  const login = async (email, password) => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.login({ email, password });
      if (result.success) {
        const userData = result.data.user || {
          key: `usr_${Date.now()}`,
          name: email.split('@')[0],
          email: email,
        };
        setUser(userData);
        return { success: true, user: userData };
      } else {
        setError(result.error || 'Login failed');
        return { success: false, error: result.error };
      }
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    setUser(null);
    // Reset LaunchDarkly to anonymous user
    if (ldClient) {
      ldClient.identify({
        kind: 'user',
        key: 'anonymous-' + Math.random().toString(36).substr(2, 9),
        anonymous: true,
      });
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        error,
        login,
        logout,
        isAuthenticated: !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

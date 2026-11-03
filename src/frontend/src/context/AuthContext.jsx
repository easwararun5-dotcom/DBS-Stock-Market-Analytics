import { createContext, useContext, useState, useEffect } from 'react';
import api from '../api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Check current session on mount
  useEffect(() => {
    const token = localStorage.getItem('dbs_token');
    api.me()
      .then(res => {
        if (res && res.user) {
          setUser(res.user);
        }
      })
      .catch(() => {
        // If token was invalid or expired, clear it
        if (token) localStorage.removeItem('dbs_token');
        setUser(null);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  const login = async (email, password) => {
    const res = await api.login({ email, password });
    if (res.access_token) {
      localStorage.setItem('dbs_token', res.access_token);
    }
    setUser(res.user);
    return res;
  };

  const register = async (name, email, password) => {
    const res = await api.register({ name, email, password });
    if (res.access_token) {
      localStorage.setItem('dbs_token', res.access_token);
    }
    setUser(res.user);
    return res;
  };

  const logout = async () => {
    try {
      await api.logout();
    } catch (e) {
      // Ignore logout network errors
    } finally {
      localStorage.removeItem('dbs_token');
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, isAuthenticated: !!user }}>
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

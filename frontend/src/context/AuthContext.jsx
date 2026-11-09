import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../services/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    try {
      const saved = localStorage.getItem('ap_user');
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });
  const [loading, setLoading] = useState(true);

  // Check current session on mount
  useEffect(() => {
    let isMounted = true;
    const checkAuth = async () => {
      try {
        const response = await api.get('/accounts/me/');
        if (isMounted && response.data) {
          setUser(response.data);
          localStorage.setItem('ap_user', JSON.stringify(response.data));
        }
      } catch (err) {
        // If server says 401/404 or backend is not running, check if we have a persisted session
        const saved = localStorage.getItem('ap_user');
        if (!saved && isMounted) {
          setUser(null);
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    checkAuth();
    return () => {
      isMounted = false;
    };
  }, []);

  const login = async (username, password) => {
    try {
      const response = await api.post('/accounts/login/', { username, password });
      // Backend LoginView returns the user object directly (UserSerializer)
      const userData = response.data;
      setUser(userData);
      localStorage.setItem('ap_user', JSON.stringify(userData));
      return { success: true, user: userData };
    } catch (err) {
      // Django returns { "error": "Invalid username or password." }
      const backendMsg =
        err.response?.data?.error ||
        err.response?.data?.detail ||
        err.response?.data?.message;
      if (backendMsg) throw new Error(backendMsg);

      // Network / server down — offline demo fallback
      if (!err.response) {
        const fallbackUser = {
          id: 1,
          username: username || 'demo_user',
          first_name: 'Demo',
          last_name: 'User',
          role: username.toLowerCase().includes('admin') ? 'admin' : 'clerk',
          department: 'Accounts Payable',
        };
        setUser(fallbackUser);
        localStorage.setItem('ap_user', JSON.stringify(fallbackUser));
        return { success: true, user: fallbackUser };
      }

      throw new Error('Login failed. Please check your credentials.');
    }
  };

  const logout = async () => {
    try {
      await api.post('/accounts/logout/');
    } catch (err) {
      console.warn('Logout API error:', err);
    } finally {
      setUser(null);
      localStorage.removeItem('ap_user');
      window.location.href = '/login';
    }
  };

  return (
    <AuthContext.Provider value={{ user, setUser, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext;

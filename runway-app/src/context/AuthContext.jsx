import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../api/client.js';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Initialize auth - run only once on mount
    const initializeAuth = async () => {
      if (token) {
        // Token exists, verify it
        api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
        await fetchCurrentUser();
      } else {
        // No token - try auto-login in dev mode
        const devAutoLogin = async () => {
          try {
            const devUsername = 'test@example.com';
            const devPassword = 'testpassword123';
            
            const response = await api.post('/auth/login', { username: devUsername, password: devPassword });
            const { access_token } = response.data;
            
            setToken(access_token);
            localStorage.setItem('token', access_token);
            api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
            
            await fetchCurrentUser();
            console.log('DEV: Auto-logged in as', devUsername);
          } catch (error) {
            console.error('DEV auto-login failed:', error);
            // Only set loading to false if auto-login fails
            setLoading(false);
          }
        };
        
        // Try auto-login in dev mode
        devAutoLogin();
      }
    };

    initializeAuth();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Empty dependency array - only run on mount

  const fetchCurrentUser = async () => {
    try {
      const response = await api.get('/auth/me');
      setUser(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch current user:', error);
      // Token is invalid, clear it but don't redirect immediately
      // Let the ProtectedRoute handle the redirect
      setToken(null);
      setUser(null);
      localStorage.removeItem('token');
      delete api.defaults.headers.common['Authorization'];
      setLoading(false);
    }
  };

  const login = async (username, password) => {
    try {
      const response = await api.post('/auth/login', { username, password });
      const { access_token } = response.data;
      
      setToken(access_token);
      localStorage.setItem('token', access_token);
      api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      
      // Fetch user info
      await fetchCurrentUser();
      
      return { success: true };
    } catch (error) {
      console.error('Login failed:', error);
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Login failed' 
      };
    }
  };

  const register = async (username, email, password) => {
    try {
      await api.post('/auth/register', { username, email, password });
      
      // Automatically log in after registration
      const result = await login(username, password);
      return result;
    } catch (error) {
      console.error('Registration failed:', error);
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Registration failed' 
      };
    }
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('token');
    delete api.defaults.headers.common['Authorization'];
    setLoading(false);
  };

  const isAuthenticated = !!user && !!token;

  const value = {
    user,
    token,
    loading,
    login,
    register,
    logout,
    isAuthenticated,
    fetchCurrentUser
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};


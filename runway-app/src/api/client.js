// src/api/client.js
import axios from 'axios';

/**
 * Base API configuration for FIRE-runway backend integration
 *
 * Features:
 * - Automatic auth token injection
 * - Request/response interceptors
 * - Error handling
 * - Token refresh on 401
 */

// Get base URL from environment or default to localhost
const BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

// Create axios instance with default config - export as 'api' to match AuthContext
const apiClient = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  timeout: 30000, // 30 seconds
  headers: {
    'Content-Type': 'application/json',
  },
});

// Export as default for compatibility
const api = apiClient;

/**
 * Request Interceptor
 * - Adds JWT token to Authorization header
 * - Logs outgoing requests in development
 */
apiClient.interceptors.request.use(
  (config) => {
    // Get auth token from localStorage (check both 'token' and 'auth_token' for compatibility)
    const token = localStorage.getItem('token') || localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // Log requests in development
    if (process.env.NODE_ENV === 'development') {
      console.log(`[API] ${config.method.toUpperCase()} ${config.url}`, config.data || '');
    }

    return config;
  },
  (error) => {
    console.error('[API] Request error:', error);
    return Promise.reject(error);
  }
);

/**
 * Response Interceptor
 * - Handles common errors (401, 403, 500)
 * - Auto token refresh on 401
 * - Logs responses in development
 */
apiClient.interceptors.response.use(
  (response) => {
    // Log successful responses in development
    if (process.env.NODE_ENV === 'development') {
      console.log(`[API] Response ${response.status}:`, response.data);
    }
    return response;
  },
  async (error) => {
    const originalRequest = error.config;

    // Handle 401 Unauthorized - redirect to login
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      // Try to refresh token
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const response = await axios.post(`${BASE_URL}/api/v1/auth/refresh`, {
            refresh_token: refreshToken,
          });

          const { access_token } = response.data;
          localStorage.setItem('auth_token', access_token);

          // Retry original request with new token
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return apiClient(originalRequest);
        } catch (refreshError) {
          // Refresh failed, clear tokens and redirect to login
          localStorage.removeItem('auth_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
          return Promise.reject(refreshError);
        }
      } else {
        // No refresh token, redirect to login
        window.location.href = '/login';
      }
    }

    // Handle 403 Forbidden
    if (error.response?.status === 403) {
      console.error('[API] Access forbidden:', error.response.data);
      // Could show a toast notification here
    }

    // Handle 500 Server Error
    if (error.response?.status === 500) {
      console.error('[API] Server error:', error.response.data);
      // Could show a toast notification with retry option
    }

    // Log all errors in development
    if (process.env.NODE_ENV === 'development') {
      console.error('[API] Error:', {
        status: error.response?.status,
        message: error.message,
        data: error.response?.data,
      });
    }

    return Promise.reject(error);
  }
);

/**
 * Helper function to handle API errors consistently
 */
export const handleApiError = (error, defaultMessage = 'An error occurred') => {
  if (error.response) {
    // Server responded with error status
    return {
      message: error.response.data?.error || error.response.data?.detail || defaultMessage,
      status: error.response.status,
      data: error.response.data,
    };
  } else if (error.request) {
    // Request made but no response
    return {
      message: 'No response from server. Please check your connection.',
      status: 0,
      data: null,
    };
  } else {
    // Something else went wrong
    return {
      message: error.message || defaultMessage,
      status: 0,
      data: null,
    };
  }
};

export default api;
export { apiClient };

import axios, { AxiosError, AxiosResponse, InternalAxiosRequestConfig } from 'axios';

const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// Flag to prevent multiple refresh attempts
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: unknown) => void;
  reject: (reason?: any) => void;
}> = [];

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

// Request interceptor - add auth token
apiClient.interceptors.request.use(
  (config) => {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor - handle errors and refresh tokens
apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError<any>) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };
    const status = error.response?.status;
    
    // Handle 401 - try to refresh token
    if (status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        // Wait for the refresh to complete
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return apiClient(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = typeof window !== 'undefined' ? localStorage.getItem('refreshToken') : null;
      
      if (refreshToken) {
        try {
          const response = await axios.post(
            `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/auth/refresh`,
            null,
            { params: { refresh_token: refreshToken } }
          );
          
          const { access_token, refresh_token: newRefreshToken } = response.data;
          
          if (typeof window !== 'undefined') {
            localStorage.setItem('token', access_token);
            localStorage.setItem('refreshToken', newRefreshToken);
          }
          
          processQueue(null, access_token);
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return apiClient(originalRequest);
        } catch (refreshError) {
          processQueue(refreshError, null);
          // Clear tokens and redirect to login
          if (typeof window !== 'undefined') {
            localStorage.removeItem('token');
            localStorage.removeItem('refreshToken');
            localStorage.removeItem('user');
            window.location.href = '/login';
          }
          return Promise.reject(refreshError);
        } finally {
          isRefreshing = false;
        }
      } else {
        // No refresh token, redirect to login
        if (typeof window !== 'undefined') {
          localStorage.removeItem('token');
          localStorage.removeItem('user');
          window.location.href = '/login';
        }
      }
    } else if (status === 429) {
      // Rate limit exceeded
      const retryAfter = error.response?.headers['retry-after'];
      const message = error.response?.data?.detail || 'Rate limit exceeded. Please try again later.';
      
      if (typeof window !== 'undefined' && (window as any).showToast) {
        (window as any).showToast({
          variant: 'destructive',
          title: 'Rate Limit Exceeded',
          description: retryAfter 
            ? `Please wait ${retryAfter} seconds before trying again.`
            : message,
        });
      }
    } else if (status === 403) {
      // Forbidden - might be 2FA required
      const detail = error.response?.data?.detail || '';
      if (detail.toLowerCase().includes('2fa')) {
        if (typeof window !== 'undefined') {
          window.location.href = '/login?requires2fa=true';
        }
      }
    } else if (status === 500) {
      if (typeof window !== 'undefined' && (window as any).showToast) {
        (window as any).showToast({
          variant: 'destructive',
          title: 'Server Error',
          description: 'Something went wrong. Please try again later.',
        });
      }
    }
    
    return Promise.reject(error);
  }
);

export default apiClient;

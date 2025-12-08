"use client";

import React, { createContext, useContext, useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import apiClient from '@/lib/api-client';
import type { User, LoginRequest, RegisterRequest, AuthResponse } from '@/types';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  // Load user from localStorage on mount
  useEffect(() => {
    const loadUser = async () => {
      try {
        const token = localStorage.getItem('token');
        const storedUser = localStorage.getItem('user');

        if (token && storedUser) {
          setUser(JSON.parse(storedUser));
          // Optionally verify token with backend
          try {
            const response = await apiClient.get('/api/v1/users/me');
            setUser(response.data);
            localStorage.setItem('user', JSON.stringify(response.data));
          } catch (error) {
            // Token invalid, clear storage
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            setUser(null);
          }
        }
      } catch (error) {
        console.error('Failed to load user:', error);
      } finally {
        setIsLoading(false);
      }
    };

    loadUser();
  }, []);

  const login = async (credentials: LoginRequest) => {
    try {
      const response = await apiClient.post<AuthResponse & { refresh_token?: string }>(
        '/api/v1/auth/login',
        credentials
      );

      const { access_token, refresh_token } = response.data;
      localStorage.setItem('token', access_token);
      if (refresh_token) {
        localStorage.setItem('refreshToken', refresh_token);
      }

      // Fetch user details
      const userResponse = await apiClient.get<User>('/api/v1/users/me');
      setUser(userResponse.data);
      localStorage.setItem('user', JSON.stringify(userResponse.data));

      router.push('/dashboard');
    } catch (error: any) {
      throw new Error(
        error.response?.data?.detail || 'Login failed. Please check your credentials.'
      );
    }
  };

  const register = async (data: RegisterRequest) => {
    try {
      await apiClient.post('/api/v1/auth/register', data);
      // Auto-login after registration
      await login({ email: data.email, password: data.password });
    } catch (error: any) {
      throw new Error(
        error.response?.data?.detail || 'Registration failed. Please try again.'
      );
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('user');
    setUser(null);
    router.push('/login');
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

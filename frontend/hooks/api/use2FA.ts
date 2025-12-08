/**
 * React Query hooks for 2FA/TOTP operations
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';

interface TOTPSetupResponse {
  secret: string;
  qr_code: string;
  uri: string;
}

interface TOTPStatusResponse {
  enabled: boolean;
}

interface TOTPVerifyRequest {
  token: string;
}

interface TOTPDisableRequest {
  password: string;
  totp_token: string;
}

export function use2FAStatus() {
  return useQuery({
    queryKey: ['2fa-status'],
    queryFn: async () => {
      const response = await apiClient.get<TOTPStatusResponse>('/api/v1/totp/status');
      return response.data;
    },
  });
}

export function useSetup2FA() {
  return useMutation({
    mutationFn: async () => {
      const response = await apiClient.post<TOTPSetupResponse>('/api/v1/totp/setup');
      return response.data;
    },
  });
}

export function useVerify2FA() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: TOTPVerifyRequest) => {
      const response = await apiClient.post<TOTPStatusResponse>('/api/v1/totp/verify', data);
      return response.data;
    },
    onSuccess: () => {
      // Invalidate 2FA status query
      queryClient.invalidateQueries({ queryKey: ['2fa-status'] });
    },
  });
}

export function useDisable2FA() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: TOTPDisableRequest) => {
      const response = await apiClient.post<TOTPStatusResponse>('/api/v1/totp/disable', data);
      return response.data;
    },
    onSuccess: () => {
      // Invalidate 2FA status query
      queryClient.invalidateQueries({ queryKey: ['2fa-status'] });
    },
  });
}

export function useLoginWith2FA() {
  return useMutation({
    mutationFn: async (data: { email: string; password: string; totp_token: string }) => {
      const response = await apiClient.post('/api/v1/auth/login-2fa', data);
      return response.data;
    },
  });
}

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import type { BrokerConnection } from '@/types';
import { useToast } from '@/hooks/use-toast';

interface ConnectionCreateRequest {
  broker_name: string;
  account_number?: string;
  server?: string;
  nickname?: string;
}

interface ConnectionStatus {
  id: string;
  status: 'online' | 'offline' | 'connecting' | 'error';
  is_connected: boolean;
  last_heartbeat?: string;
  account_info?: Record<string, any>;
}

// Fetch all connections
export function useConnections() {
  return useQuery<BrokerConnection[]>({
    queryKey: ['connections'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/brokers/connections');
      return response.data;
    },
  });
}

// Get connection status
export function useConnectionStatus(connectionId: string | null) {
  return useQuery<ConnectionStatus>({
    queryKey: ['connection-status', connectionId],
    queryFn: async () => {
      if (!connectionId) throw new Error('No connection ID');
      const response = await apiClient.get(`/api/v1/brokers/connections/${connectionId}/status`);
      return response.data;
    },
    enabled: !!connectionId,
    refetchInterval: 10000, // Refresh every 10 seconds
  });
}

// Create connection
export function useCreateConnection() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async (data: ConnectionCreateRequest) => {
      const response = await apiClient.post('/api/v1/brokers/connections', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connections'] });
      toast({
        title: 'Success',
        description: 'Broker connection created',
      });
    },
    onError: (error: any) => {
      toast({
        variant: 'destructive',
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to create connection',
      });
    },
  });
}

// Delete connection
export function useDeleteConnection() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async (connectionId: string) => {
      await apiClient.delete(`/api/v1/brokers/connections/${connectionId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connections'] });
      toast({
        title: 'Success',
        description: 'Connection deleted',
      });
    },
    onError: (error: any) => {
      toast({
        variant: 'destructive',
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to delete connection',
      });
    },
  });
}

// Sync connection
export function useSyncConnection() {
  const { toast } = useToast();

  return useMutation({
    mutationFn: async (connectionId: string) => {
      const response = await apiClient.post(`/api/v1/brokers/connections/${connectionId}/sync`);
      return response.data;
    },
    onSuccess: (data) => {
      toast({
        title: data.synced ? 'Sync Started' : 'Sync Failed',
        description: data.message,
      });
    },
    onError: (error: any) => {
      toast({
        variant: 'destructive',
        title: 'Sync Error',
        description: error.response?.data?.detail || 'Failed to sync',
      });
    },
  });
}

// Get supported brokers
export function useSupportedBrokers() {
  return useQuery({
    queryKey: ['supported-brokers'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/brokers/supported-brokers');
      return response.data;
    },
  });
}

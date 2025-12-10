import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import type { 
  Position, 
  Trade, 
  OrderCreate, 
  DashboardStats,
  CalculateSLTPRequest,
  CalculateSLTPResponse,
  RiskProfile,
} from '@/types';
import { useToast } from '@/hooks/use-toast';

// Fetch positions
export function usePositions() {
  return useQuery<Position[]>({
    queryKey: ['positions'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/trading/positions');
      return response.data;
    },
  });
}

// Fetch trade history
export function useTrades() {
  return useQuery<Trade[]>({
    queryKey: ['trades'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/trading/history');
      return response.data;
    },
  });
}

// Place order mutation
export function usePlaceOrder() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async (order: OrderCreate) => {
      const response = await apiClient.post('/api/v1/trading/orders', order);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['positions'] });
      queryClient.invalidateQueries({ queryKey: ['trades'] });
      toast({
        title: 'Success',
        description: 'Order placed successfully',
      });
    },
    onError: (error: any) => {
      toast({
        variant: 'destructive',
        title: 'Order Failed',
        description: error.response?.data?.detail || 'Failed to place order',
      });
    },
  });
}

// Close position mutation
export function useClosePosition() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async ({ orderId, closePrice }: { orderId: string; closePrice: number }) => {
      const response = await apiClient.put(
        `/api/v1/trading/orders/${orderId}/close`,
        { close_price: closePrice }
      );
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['positions'] });
      queryClient.invalidateQueries({ queryKey: ['trades'] });
      toast({
        title: 'Success',
        description: 'Position closed successfully',
      });
    },
    onError: (error: any) => {
      toast({
        variant: 'destructive',
        title: 'Close Failed',
        description: error.response?.data?.detail || 'Failed to close position',
      });
    },
  });
}

// Calculate position size
export function useCalculatePositionSize() {
  return useMutation({
    mutationFn: async (data: {
      account_balance: number;
      risk_percent: number;
      entry_price: number;
      stop_loss: number;
      symbol: string;
    }) => {
      const response = await apiClient.post('/api/v1/trading/position-size/calculate', data);
      return response.data;
    },
  });
}

// Fetch dashboard stats
export function useDashboardStats() {
  return useQuery<DashboardStats>({
    queryKey: ['dashboard-stats'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/trading/dashboard/stats');
      return response.data;
    },
    refetchInterval: 30000, // Refetch every 30 seconds
  });
}

// Calculate SL/TP based on risk management settings
export function useCalculateSLTP() {
  return useMutation<CalculateSLTPResponse, Error, CalculateSLTPRequest>({
    mutationFn: async (data) => {
      const response = await apiClient.post('/api/v1/trading/calculate-sl-tp', data);
      return response.data;
    },
  });
}

// Fetch risk profiles
export function useRiskProfiles() {
  return useQuery<{ profiles: Record<string, RiskProfile> }>({
    queryKey: ['risk-profiles'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/trading/risk-profiles');
      return response.data;
    },
    staleTime: 1000 * 60 * 60, // Cache for 1 hour
  });
}

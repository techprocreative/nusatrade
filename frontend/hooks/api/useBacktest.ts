import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import type { BacktestConfig, BacktestResult } from '@/types';
import { useToast } from '@/hooks/use-toast';

// Fetch backtest strategies (preset strategies for backtesting)
export function useBacktestStrategies() {
  return useQuery({
    queryKey: ['backtest-strategies'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/backtest/strategies');
      return response.data;
    },
  });
}

// Fetch backtest sessions
export function useBacktestSessions() {
  return useQuery({
    queryKey: ['backtest-sessions'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/backtest/sessions');
      return response.data;
    },
  });
}

// Run backtest
export function useRunBacktest() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async (config: BacktestConfig) => {
      const response = await apiClient.post('/api/v1/backtest/run', config);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['backtest-sessions'] });
      toast({
        title: 'Backtest Started',
        description: 'Backtest is running. Results will be available shortly.',
      });
    },
    onError: (error: any) => {
      toast({
        variant: 'destructive',
        title: 'Backtest Failed',
        description: error.response?.data?.detail || 'Failed to start backtest',
      });
    },
  });
}

// Get backtest result
export function useBacktestResult(sessionId: string | null) {
  return useQuery<BacktestResult>({
    queryKey: ['backtest-result', sessionId],
    queryFn: async () => {
      if (!sessionId) throw new Error('No session ID');
      const response = await apiClient.get(`/api/v1/backtest/sessions/${sessionId}`);
      return response.data;
    },
    enabled: !!sessionId,
  });
}

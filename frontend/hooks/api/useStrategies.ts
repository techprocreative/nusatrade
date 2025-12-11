import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import type {
  TradingStrategy,
  AIStrategyRequest,
  AIStrategyResponse,
  CreateStrategyRequest,
  QuickBacktestRequest,
  BacktestMetrics,
} from '@/types';
import { useToast } from '@/hooks/use-toast';

// Fetch all strategies
export function useStrategies() {
  return useQuery<TradingStrategy[]>({
    queryKey: ['strategies'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/strategies');
      return response.data;
    },
  });
}

// Fetch single strategy
export function useStrategy(id: string | null) {
  return useQuery<TradingStrategy>({
    queryKey: ['strategy', id],
    queryFn: async () => {
      if (!id) throw new Error('No strategy ID');
      const response = await apiClient.get(`/api/v1/strategies/${id}`);
      return response.data;
    },
    enabled: !!id,
  });
}

// Generate strategy with AI using SSE streaming
export function useGenerateStrategy() {
  const { toast } = useToast();

  return useMutation<AIStrategyResponse, Error, AIStrategyRequest & { onProgress?: (status: string) => void }>({
    mutationFn: async ({ onProgress, ...request }) => {
      const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

      return new Promise((resolve, reject) => {
        // Use fetch with streaming for SSE
        fetch(`${baseUrl}/api/v1/ai/generate-strategy-stream`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify(request),
        }).then(async (response) => {
          if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Request failed' }));
            reject(new Error(error.detail || 'Failed to generate strategy'));
            return;
          }

          const reader = response.body?.getReader();
          if (!reader) {
            reject(new Error('No response body'));
            return;
          }

          const decoder = new TextDecoder();
          let buffer = '';

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            // Parse SSE events
            const lines = buffer.split('\n\n');
            buffer = lines.pop() || '';

            for (const eventBlock of lines) {
              if (!eventBlock.trim()) continue;

              const eventLines = eventBlock.split('\n');
              let eventType = 'message';
              let data = '';

              for (const line of eventLines) {
                if (line.startsWith('event: ')) {
                  eventType = line.slice(7);
                } else if (line.startsWith('data: ')) {
                  data = line.slice(6);
                }
              }

              if (!data) continue;

              try {
                const parsed = JSON.parse(data);

                switch (eventType) {
                  case 'progress':
                    onProgress?.(parsed.status);
                    break;
                  case 'keepalive':
                    onProgress?.(`Generating... (${parsed.count * 5}s)`);
                    break;
                  case 'result':
                    resolve(parsed as AIStrategyResponse);
                    return;
                  case 'error':
                    reject(new Error(parsed.error || 'Generation failed'));
                    return;
                }
              } catch {
                // Ignore parse errors for incomplete events
              }
            }
          }

          reject(new Error('Stream ended without result'));
        }).catch(reject);
      });
    },
    onSuccess: () => {
      toast({
        title: 'Strategy Generated',
        description: 'AI has created a new trading strategy for you.',
      });
    },
    onError: (error: any) => {
      toast({
        variant: 'destructive',
        title: 'Generation Failed',
        description: error.message || 'Failed to generate strategy',
      });
    },
  });
}

// Create/Save strategy
export function useSaveStrategy() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation<TradingStrategy, Error, CreateStrategyRequest>({
    mutationFn: async (strategy) => {
      const response = await apiClient.post('/api/v1/strategies', strategy);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategies'] });
      toast({
        title: 'Strategy Saved',
        description: 'Your strategy has been saved successfully.',
      });
    },
    onError: (error: any) => {
      toast({
        variant: 'destructive',
        title: 'Save Failed',
        description: error.response?.data?.detail || 'Failed to save strategy',
      });
    },
  });
}

// Update strategy
export function useUpdateStrategy() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation<TradingStrategy, Error, { id: string; data: Partial<CreateStrategyRequest> }>({
    mutationFn: async ({ id, data }) => {
      const response = await apiClient.put(`/api/v1/strategies/${id}`, data);
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['strategies'] });
      queryClient.invalidateQueries({ queryKey: ['strategy', variables.id] });
      toast({
        title: 'Strategy Updated',
        description: 'Your strategy has been updated successfully.',
      });
    },
    onError: (error: any) => {
      toast({
        variant: 'destructive',
        title: 'Update Failed',
        description: error.response?.data?.detail || 'Failed to update strategy',
      });
    },
  });
}

// Delete strategy
export function useDeleteStrategy() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation<void, Error, string>({
    mutationFn: async (id) => {
      await apiClient.delete(`/api/v1/strategies/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategies'] });
      toast({
        title: 'Strategy Deleted',
        description: 'Strategy has been removed.',
      });
    },
    onError: (error: any) => {
      toast({
        variant: 'destructive',
        title: 'Delete Failed',
        description: error.response?.data?.detail || 'Failed to delete strategy',
      });
    },
  });
}

// Toggle strategy active status
export function useToggleStrategy() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation<TradingStrategy, Error, { id: string; isActive: boolean }>({
    mutationFn: async ({ id, isActive }) => {
      const response = await apiClient.patch(`/api/v1/strategies/${id}/toggle`, {
        is_active: isActive,
      });
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['strategies'] });
      toast({
        title: variables.isActive ? 'Strategy Activated' : 'Strategy Deactivated',
        description: `Strategy has been ${variables.isActive ? 'activated' : 'deactivated'}.`,
      });
    },
    onError: (error: any) => {
      toast({
        variant: 'destructive',
        title: 'Toggle Failed',
        description: error.response?.data?.detail || 'Failed to toggle strategy',
      });
    },
  });
}

// Quick backtest strategy
export function useQuickBacktest() {
  const { toast } = useToast();

  return useMutation<BacktestMetrics, Error, QuickBacktestRequest>({
    mutationFn: async (request) => {
      const response = await apiClient.post(
        `/api/v1/strategies/${request.strategy_id}/quick-backtest`,
        {
          symbol: request.symbol,
          timeframe: request.timeframe,
          days: request.days || 30,
        }
      );
      return response.data;
    },
    onSuccess: () => {
      toast({
        title: 'Backtest Complete',
        description: 'Quick backtest has finished.',
      });
    },
    onError: (error: any) => {
      toast({
        variant: 'destructive',
        title: 'Backtest Failed',
        description: error.response?.data?.detail || 'Failed to run backtest',
      });
    },
  });
}

// Validate strategy
export function useValidateStrategy() {
  return useMutation<{ valid: boolean; errors: string[] }, Error, string>({
    mutationFn: async (strategyId) => {
      const response = await apiClient.post(`/api/v1/strategies/${strategyId}/validate`);
      return response.data;
    },
  });
}

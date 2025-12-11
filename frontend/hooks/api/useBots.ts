import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import type { MLModel, MLPrediction } from '@/types';
import { useToast } from '@/hooks/use-toast';

// Fetch ML models
export function useMLModels() {
  return useQuery<MLModel[]>({
    queryKey: ['ml-models'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/ml/models');
      return response.data;
    },
  });
}

// Helper to safely extract error message
const getErrorMessage = (error: any): string => {
  const detail = error.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map(d => d.msg).join(', ');
  if (typeof detail === 'object') return JSON.stringify(detail);
  return 'An unexpected error occurred';
};

// Create ML model
export function useCreateMLModel() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async (data: {
      name: string;
      model_type: string;
      symbol: string;
      timeframe: string;
      strategy_id?: string;
      config?: Record<string, any>;
    }) => {
      const response = await apiClient.post('/api/v1/ml/models', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ml-models'] });
      toast({
        title: 'Success',
        description: 'ML model created successfully',
      });
    },
    onError: (error: any) => {
      toast({
        variant: 'destructive',
        title: 'Creation Failed',
        description: getErrorMessage(error),
      });
    },
  });
}

// Toggle model activation
export function useToggleMLModel() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async ({ modelId, isActive }: { modelId: string; isActive: boolean }) => {
      // Use separate activate/deactivate endpoints as per backend API
      const endpoint = isActive ? 'activate' : 'deactivate';
      const response = await apiClient.post(`/api/v1/ml/models/${modelId}/${endpoint}`);
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['ml-models'] });
      toast({
        title: variables.isActive ? 'Model Activated' : 'Model Deactivated',
        description: `Model has been ${variables.isActive ? 'activated' : 'deactivated'}`,
      });
    },
    onError: (error: any) => {
      toast({
        variant: 'destructive',
        title: 'Update Failed',
        description: getErrorMessage(error),
      });
    },
  });
}

// Train model
export function useTrainMLModel() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async (modelId: string) => {
      const response = await apiClient.post(`/api/v1/ml/models/${modelId}/train`, {});
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['ml-models'] });
      if (data.status === 'completed') {
        toast({
          title: 'Training Completed',
          description: `Model trained successfully. Accuracy: ${(data.metrics?.accuracy * 100 || 0).toFixed(1)}%`,
        });
      } else if (data.status === 'failed') {
        toast({
          variant: 'destructive',
          title: 'Training Failed',
          description: data.message || 'Training failed',
        });
      }
    },
    onError: (error: any) => {
      queryClient.invalidateQueries({ queryKey: ['ml-models'] });
      toast({
        variant: 'destructive',
        title: 'Training Failed',
        description: getErrorMessage(error),
      });
    },
  });
}

// Get training status
export function useTrainingStatus(modelId: string | null, enabled: boolean = false) {
  return useQuery<{
    id: string;
    training_status: string;
    training_error?: string;
    performance_metrics?: Record<string, any>;
  }>({
    queryKey: ['training-status', modelId],
    queryFn: async () => {
      if (!modelId) throw new Error('No model ID');
      const response = await apiClient.get(`/api/v1/ml/models/${modelId}/status`);
      return response.data;
    },
    enabled: !!modelId && enabled,
    refetchInterval: enabled ? 2000 : false, // Poll every 2s when enabled
  });
}

// Delete model
export function useDeleteMLModel() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async (modelId: string) => {
      await apiClient.delete(`/api/v1/ml/models/${modelId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ml-models'] });
      toast({
        title: 'Success',
        description: 'Model deleted successfully',
      });
    },
    onError: (error: any) => {
      toast({
        variant: 'destructive',
        title: 'Delete Failed',
        description: getErrorMessage(error),
      });
    },
  });
}

// Get prediction from model
export function useGetPrediction() {
  const { toast } = useToast();

  return useMutation<MLPrediction, Error, { modelId: string; symbol: string }>({
    mutationFn: async ({ modelId, symbol }) => {
      const response = await apiClient.post(`/api/v1/ml/models/${modelId}/predict`, { symbol });
      return response.data;
    },
    onSuccess: () => {
      toast({
        title: 'Signal Generated',
        description: 'ML prediction has been generated successfully.',
      });
    },
    onError: (error: any) => {
      toast({
        variant: 'destructive',
        title: 'Prediction Failed',
        description: getErrorMessage(error),
      });
    },
  });
}

// Execute trade from prediction
export function useExecutePrediction() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async (data: {
      modelId: string;
      predictionId: string;
      lotSize: number;
      connectionId?: string;
    }) => {
      const response = await apiClient.post(`/api/v1/ml/models/${data.modelId}/execute`, {
        prediction_id: data.predictionId,
        lot_size: data.lotSize,
        connection_id: data.connectionId,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['positions'] });
      queryClient.invalidateQueries({ queryKey: ['trades'] });
      toast({
        title: 'Trade Executed',
        description: 'Trade has been executed from ML signal.',
      });
    },
    onError: (error: any) => {
      toast({
        variant: 'destructive',
        title: 'Execution Failed',
        description: getErrorMessage(error),
      });
    },
  });
}

// Get prediction history
export function usePredictionHistory(modelId: string | null) {
  return useQuery<MLPrediction[]>({
    queryKey: ['predictions', modelId],
    queryFn: async () => {
      if (!modelId) throw new Error('No model ID');
      const response = await apiClient.get(`/api/v1/ml/models/${modelId}/predictions`);
      return response.data;
    },
    enabled: !!modelId,
  });
}

// Active bots data type
export interface ActiveBotData {
  id: string;
  name: string;
  model_type: string;
  symbol: string;
  timeframe: string;
  strategy_name?: string;
  accuracy: number;
  last_prediction?: {
    direction: 'BUY' | 'SELL' | 'HOLD';
    confidence: number;
    entry_price?: number;
    created_at?: string;
  };
  today_signals: number;
  is_active: boolean;
}

export interface ActiveBotsResponse {
  active_count: number;
  bots: ActiveBotData[];
  total_signals_today: number;
}

// Get active bots for dashboard
export function useActiveBots() {
  return useQuery<ActiveBotsResponse>({
    queryKey: ['active-bots'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/ml/dashboard/active-bots');
      return response.data;
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });
}

// Auto-trading status
export interface AutoTradingStatus {
  scheduler_running: boolean;
  interval_minutes: number;
  active_models: number;
  predictions_today: number;
  last_run: string | null;
  config: {
    default_confidence_threshold: number;
    default_max_trades_per_day: number;
    default_cooldown_minutes: number;
  };
}

export function useAutoTradingStatus() {
  return useQuery<AutoTradingStatus>({
    queryKey: ['auto-trading-status'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/ml/auto-trading/status');
      return response.data;
    },
    refetchInterval: 60000, // Refresh every minute
  });
}

// Trigger auto-trading manually
export function useTriggerAutoTrading() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async () => {
      const response = await apiClient.post('/api/v1/ml/auto-trading/trigger');
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['auto-trading-status'] });
      queryClient.invalidateQueries({ queryKey: ['active-bots'] });
      queryClient.invalidateQueries({ queryKey: ['positions'] });
      queryClient.invalidateQueries({ queryKey: ['trades'] });

      const result = data.result;
      toast({
        title: 'Auto-Trading Triggered',
        description: `Checked ${result.models_checked} models. Predictions: ${result.predictions_generated}, Trades: ${result.trades_executed}`,
      });
    },
    onError: (error: any) => {
      toast({
        variant: 'destructive',
        title: 'Trigger Failed',
        description: getErrorMessage(error),
      });
    },
  });
}

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
        description: error.response?.data?.detail || 'Failed to create model',
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
        description: error.response?.data?.detail || 'Failed to update model',
      });
    },
  });
}

// Train model
export function useTrainMLModel() {
  const { toast } = useToast();

  return useMutation({
    mutationFn: async (modelId: string) => {
      const response = await apiClient.post(`/api/v1/ml/models/${modelId}/train`);
      return response.data;
    },
    onSuccess: () => {
      toast({
        title: 'Training Started',
        description: 'Model training has been initiated. This may take a few minutes.',
      });
    },
    onError: (error: any) => {
      toast({
        variant: 'destructive',
        title: 'Training Failed',
        description: error.response?.data?.detail || 'Failed to start training',
      });
    },
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
        description: error.response?.data?.detail || 'Failed to delete model',
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
        description: error.response?.data?.detail || 'Failed to get prediction',
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
        description: error.response?.data?.detail || 'Failed to execute trade',
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

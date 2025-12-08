import { useMutation } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import type { ChatRequest, ChatResponse } from '@/types';
import { useToast } from '@/hooks/use-toast';

// Send chat message
export function useSendMessage() {
  const { toast } = useToast();

  return useMutation({
    mutationFn: async (data: ChatRequest) => {
      const response = await apiClient.post<ChatResponse>('/api/v1/ai/chat', data);
      return response.data;
    },
    onError: (error: any) => {
      toast({
        variant: 'destructive',
        title: 'AI Error',
        description: error.response?.data?.detail || 'Failed to get AI response',
      });
    },
  });
}

// Get daily analysis
export function useGetDailyAnalysis() {
  return useMutation({
    mutationFn: async () => {
      const response = await apiClient.get('/api/v1/ai/analysis/daily');
      return response.data;
    },
  });
}

// Get symbol analysis
export function useGetSymbolAnalysis() {
  return useMutation({
    mutationFn: async (symbol: string) => {
      const response = await apiClient.get(`/api/v1/ai/analysis/${symbol}`);
      return response.data;
    },
  });
}

// Get recommendations
export function useGetRecommendations() {
  return useMutation({
    mutationFn: async () => {
      const response = await apiClient.get('/api/v1/ai/recommendations');
      return response.data;
    },
  });
}

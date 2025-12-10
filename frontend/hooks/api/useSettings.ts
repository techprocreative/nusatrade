import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import { useToast } from '@/hooks/use-toast';

export interface UserSettings {
  defaultLotSize: string;
  maxLotSize: string;
  maxOpenPositions: string;
  defaultStopLoss: string;
  defaultTakeProfit: string;
  riskPerTrade: string;
  emailNotifications: boolean;
  tradeAlerts: boolean;
  dailySummary: boolean;
  llmApiKey?: string;
  llmBaseUrl?: string;
  llmModel?: string;
  theme: string;
  timezone: string;
  language: string;
}

export function useUserSettings() {
  return useQuery<UserSettings>({
    queryKey: ['user-settings'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/users/settings');
      return response.data;
    },
    staleTime: 1000 * 60 * 5, // Cache for 5 minutes
  });
}

export function useUpdateUserSettings() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async (settings: Partial<UserSettings>) => {
      const response = await apiClient.put('/api/v1/users/settings', settings);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user-settings'] });
      toast({
        title: 'Settings Saved',
        description: 'Your preferences have been updated successfully',
      });
    },
    onError: (error: any) => {
      toast({
        variant: 'destructive',
        title: 'Save Failed',
        description: error.response?.data?.detail || 'Failed to save settings',
      });
    },
  });
}

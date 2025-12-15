const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface MLModel {
  id: string;
  name: string;
  symbol: string;
  model_type: string;
  timeframe: string;
  file_path: string | null;
  is_active: boolean;
  strategy_id: string | null;
  strategy_name?: string;
  performance_metrics: {
    accuracy?: number;
    win_rate?: number;
    profit_factor?: number;
  };
  created_at: string;
}

export interface Strategy {
  id: string;
  name: string;
  description: string;
  symbol: string;
  config: Record<string, any>;
}

export interface StrategyTemplate {
  id: string;
  name: string;
  description: string;
  risk_level: string;
  recommended_for: string[];
}

// Fetch all ML models
export async function getMLModels(token: string): Promise<MLModel[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/ml/models`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  if (!res.ok) throw new Error('Failed to fetch models');
  return res.json();
}

// Get strategies for symbol
export async function getStrategiesForSymbol(symbol: string, token: string): Promise<Strategy[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/ml/strategies/for-model/${symbol}`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  if (!res.ok) throw new Error('Failed to fetch strategies');
  const data = await res.json();
  return data.strategies;
}

// Link model to strategy
export async function linkModelToStrategy(
  modelId: string,
  strategyId: string,
  token: string
): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/v1/ml/models/${modelId}/link-strategy`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify({ strategy_id: strategyId })
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || 'Failed to link strategy');
  }
}

// Activate model
export async function activateModel(modelId: string, token: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/v1/ml/models/${modelId}/activate`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` }
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || 'Failed to activate model');
  }
}

// Deactivate model
export async function deactivateModel(modelId: string, token: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/v1/ml/models/${modelId}/deactivate`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` }
  });
  if (!res.ok) throw new Error('Failed to deactivate model');
}

// Get strategy templates
export async function getStrategyTemplates(token: string) {
  const res = await fetch(`${API_BASE_URL}/api/v1/strategies/templates`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  if (!res.ok) throw new Error('Failed to fetch templates');
  return res.json();
}

// Create strategy from template
export async function createStrategyFromTemplate(
  templateName: string,
  symbol: string,
  customName: string | null,
  token: string
) {
  const params = new URLSearchParams({
    template_name: templateName,
    symbol
  });
  if (customName) params.append('custom_name', customName);

  const res = await fetch(`${API_BASE_URL}/api/v1/strategies/from-template?${params}`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` }
  });
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.detail || 'Failed to create strategy');
  }
  return res.json();
}

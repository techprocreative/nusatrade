// User types
export interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  subscription_tier: string;
  created_at: string;
}

// Auth types
export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

// Trading types
export interface Position {
  id: string;
  symbol: string;
  trade_type: 'BUY' | 'SELL';
  lot_size: number;
  open_price: number;
  current_price: number;
  profit: number;
  open_time: string;
  stop_loss?: number;
  take_profit?: number;
}

export interface Trade {
  id: string;
  symbol: string;
  trade_type: 'BUY' | 'SELL';
  lot_size: number;
  open_price: number;
  close_price: number;
  profit: number;
  open_time: string;
  close_time: string;
}

export interface TrailingStopSettings {
  enabled: boolean;
  trailing_type: 'fixed_pips' | 'atr_based' | 'percentage';
  activation_pips: number;
  trail_distance_pips: number;
  atr_multiplier: number;
  breakeven_enabled: boolean;
  breakeven_pips: number;
}

export interface OrderCreate {
  symbol: string;
  order_type: 'BUY' | 'SELL';
  lot_size: number;
  price: number;
  stop_loss?: number;
  take_profit?: number;
  connection_id?: string;
  use_atr_sl?: boolean;
  sl_atr_multiplier?: number;
  tp_risk_reward?: number;
  trailing_stop?: TrailingStopSettings;
}

export interface CalculateSLTPRequest {
  symbol: string;
  direction: 'BUY' | 'SELL';
  entry_price: number;
  sl_type: 'fixed_pips' | 'atr_based' | 'percentage';
  sl_value: number;
  tp_type: 'fixed_pips' | 'risk_reward' | 'atr_based';
  tp_value: number;
  atr?: number;
}

export interface CalculateSLTPResponse {
  stop_loss: number;
  take_profit: number;
  sl_distance_pips: number;
  tp_distance_pips: number;
  risk_reward_ratio: number;
}

export interface RiskProfile {
  sl_type: string;
  sl_value: number;
  tp_type: string;
  tp_value: number;
  risk_per_trade_percent: number;
  max_position_size: number;
  trailing_stop: TrailingStopSettings | null;
}

// ML Model types
export type TrainingStatus = 'idle' | 'training' | 'completed' | 'failed';

export interface MLModel {
  id: string;
  name: string;
  model_type: string;
  symbol: string;
  timeframe: string;
  strategy_id?: string;
  strategy_name?: string;
  is_active: boolean;
  performance_metrics: {
    accuracy?: number;
    precision?: number;
    recall?: number;
    f1_score?: number;
    train_samples?: number;
    test_samples?: number;
    feature_count?: number;
    top_features?: Record<string, number>;
  } | null;
  training_status: TrainingStatus;
  training_error?: string;
  training_started_at?: string;
  training_completed_at?: string;
  created_at: string;
}

export interface StrategyValidation {
  valid: boolean;
  matched_rules: string[];
  failed_rules: string[];
  message: string;
  current_indicators?: Record<string, number>;
}

export interface MLPrediction {
  id: string;
  model_id: string;
  symbol: string;
  prediction: {
    direction: 'BUY' | 'SELL' | 'HOLD';
    confidence: number;
    entry_price: number;
    stop_loss?: number;
    take_profit?: number;
    risk_reward_ratio?: number;
    trailing_stop?: {
      enabled: boolean;
      activation_pips: number;
      trail_distance_pips: number;
      breakeven_pips: number;
    };
    ml_signal?: 'BUY' | 'SELL' | 'HOLD';
    strategy_validation?: StrategyValidation;
    should_trade?: boolean;
    current_indicators?: Record<string, number>;
    generated_by?: 'ml_model' | 'fallback';
  };
  confidence: number;
  strategy_rules?: {
    entry_rules: string[];
    exit_rules: string[];
  };
  created_at: string;
}

// Backtest types
export interface BacktestConfig {
  strategy_id: string;
  symbol: string;
  timeframe: string;
  start_date: string;
  end_date: string;
  initial_balance?: number;
  commission?: number;
  slippage?: number;
  lot_size?: number;
}

export interface BacktestTrade {
  symbol: string;
  order_type: string;
  entry_price: number;
  exit_price: number;
  profit: number;
}

export interface BacktestResult {
  session_id: string;
  status: string;
  net_profit?: number;
  total_trades?: number;
  winning_trades?: number;
  losing_trades?: number;
  win_rate?: number;
  profit_factor?: number;
  max_drawdown_pct?: number;
  sharpe_ratio?: number;
  avg_win?: number;
  avg_loss?: number;
  trades?: BacktestTrade[];
  equity_curve?: number[];
  created_at?: string;
}

export interface BacktestSession {
  id: string;
  strategy_id: string;
  symbol: string;
  timeframe: string;
  start_date: string;
  end_date: string;
  initial_balance: number;
  status: string;
  created_at: string;
  result?: BacktestResult;
}

// Broker Connection types
export interface BrokerConnection {
  id: string;
  broker_name: string;
  account_number?: string;
  server?: string;
  is_active: boolean;
  last_connected_at?: string;
  created_at: string;
}

// AI Chat types
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export interface ChatRequest {
  message: string;
  conversation_id?: string;
  context_type?: 'general' | 'trade_analysis' | 'market_summary';
}

export interface ChatResponse {
  reply: string;
  conversation_id: string;
  tokens_used: number;
}

// Dashboard types
export interface DashboardStats {
  balance: number;
  equity: number;
  open_positions: number;
  today_pnl: number;
  total_pnl: number;
  unrealized_pnl: number;
  total_trades: number;
  win_rate: number;
}

// Strategy types
export interface TradingStrategy {
  id: string;
  name: string;
  description: string;
  strategy_type: 'ai_generated' | 'custom' | 'preset';
  code: string;
  parameters: StrategyParameter[];
  indicators: string[];
  entry_rules: StrategyRule[];
  exit_rules: StrategyRule[];
  risk_management: RiskManagement;
  is_active: boolean;
  backtest_results?: BacktestMetrics;
  created_at: string;
  updated_at: string;
}

export interface StrategyParameter {
  name: string;
  type: 'number' | 'string' | 'boolean';
  default_value: string | number | boolean;
  description?: string;
  min?: number;
  max?: number;
}

export interface StrategyRule {
  id: string;
  condition: string;
  action: 'BUY' | 'SELL' | 'CLOSE';
  description: string;
}

export interface RiskManagement {
  stop_loss_type: 'fixed_pips' | 'atr_based' | 'percentage';
  stop_loss_value: number;
  take_profit_type: 'fixed_pips' | 'risk_reward' | 'atr_based';
  take_profit_value: number;
  trailing_stop?: TrailingStopSettings;
  max_position_size: number;
  risk_per_trade_percent?: number;
  max_daily_loss?: number;
}

export interface BacktestMetrics {
  net_profit: number;
  total_trades: number;
  winning_trades: number;
  win_rate: number;
  profit_factor: number;
  max_drawdown_pct: number;
  sharpe_ratio: number;
}

export interface AIStrategyRequest {
  prompt: string;
  symbol?: string;
  timeframe?: string;
  risk_profile?: 'conservative' | 'moderate' | 'aggressive';
  preferred_indicators?: string[];
}

export interface AIStrategyResponse {
  strategy: TradingStrategy;
  explanation: string;
  warnings: string[];
  suggested_improvements: string[];
}

export interface CreateStrategyRequest {
  name: string;
  description: string;
  strategy_type: 'ai_generated' | 'custom' | 'preset';
  code?: string;
  parameters?: StrategyParameter[];
  indicators?: string[];
  entry_rules?: StrategyRule[];
  exit_rules?: StrategyRule[];
  risk_management?: RiskManagement;
}

export interface QuickBacktestRequest {
  strategy_id: string;
  symbol: string;
  timeframe: string;
  days?: number;
}

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

export interface OrderCreate {
  symbol: string;
  order_type: 'BUY' | 'SELL';
  lot_size: number;
  price: number;
  stop_loss?: number;
  take_profit?: number;
  connection_id?: string;
}

// ML Model types
export interface MLModel {
  id: string;
  name: string;
  model_type: string;
  is_active: boolean;
  performance_metrics: {
    accuracy?: number;
    precision?: number;
    f1_score?: number;
  } | null;
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
}

export interface BacktestResult {
  session_id: string;
  status: string;
  metrics: {
    net_profit: number;
    total_trades: number;
    winning_trades: number;
    win_rate: number;
    profit_factor: number;
    max_drawdown_pct: number;
    sharpe_ratio: number;
  };
  trades: Trade[];
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
  context?: Record<string, any>;
}

export interface ChatResponse {
  response: string;
  conversation_id: string;
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

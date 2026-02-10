export interface StockInfo {
  id: number | null;
  symbol: string;
  name: string | null;
  exchange: string | null;
  sector: string | null;
}

export interface OHLCVBar {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface StrategyInfo {
  class_name: string;
  name: string;
  docstring: string;
  indicators: IndicatorConfig[];
}

export interface IndicatorConfig {
  name: string;
  params?: Record<string, number>;
  column?: string;
}

export interface BacktestRequest {
  name: string;
  strategy_name: string;
  symbols: string[];
  start_date: string;
  end_date: string;
  initial_capital: number;
  commission_rate: number;
  strategy_params: Record<string, unknown>;
}

export interface TradeRecord {
  id?: number;
  backtest_id: number;
  symbol: string;
  side: "BUY" | "SELL";
  quantity: number;
  price: number;
  commission: number;
  date: string;
}

export interface PerformanceMetrics {
  total_return: number;
  total_return_pct: number;
  annualized_return_pct: number;
  max_drawdown_pct: number;
  win_rate: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  sharpe_ratio: number;
  profit_factor: number;
  avg_trade_return_pct: number;
  max_consecutive_wins: number;
  max_consecutive_losses: number;
}

export interface EquityPoint {
  date: string;
  equity: number;
  cash: number;
}

export interface BacktestResult {
  backtest_id: number;
  name: string;
  strategy_name: string;
  symbols: string[];
  start_date: string;
  end_date: string;
  initial_capital: number;
  final_equity: number;
  metrics: PerformanceMetrics;
  trades: TradeRecord[];
  equity_curve: EquityPoint[];
}

export interface BacktestSummary {
  id: number;
  name: string;
  strategy_name: string;
  symbols: string[];
  start_date: string;
  end_date: string;
  initial_capital: number;
  status: string;
  created_at: string;
}

export interface DateRange {
  symbol: string;
  start_date: string;
  end_date: string;
}

// ── Authentication ──

export interface UserResponse {
  id: number;
  email: string;
  created_at: string;
}

export interface UserCreate {
  email: string;
  password: string;
}

export interface UserLogin {
  email: string;
  password: string;
}

export interface Token {
  access_token: string;
  token_type: string;
}

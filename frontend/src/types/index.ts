export type StrategyCategory = 'trend' | 'momentum' | 'fundamental' | 'composite';

export interface ParamDef {
  type: string;
  default: unknown;
  description: string;
}

export interface Strategy {
  id: number;
  name: string;
  category: StrategyCategory;
  description: string;
  params: Record<string, ParamDef>;
  code_ref?: string | null;
  backtest_count?: number;
  created_at: string;
  updated_at: string;
}

export interface CurvePoint {
  date: string;
  value: number;
}

export interface YearlyReturn {
  year: number;
  value: number;
}

export interface MonthlyReturn {
  year: number;
  month: number;
  value: number;
}

export interface BacktestResult {
  id: string;
  strategy_id: number;
  strategy_name?: string;
  stock_codes: string[];
  params: Record<string, unknown>;
  start_date: string;
  end_date: string;
  metrics: BacktestMetrics;
  equity_curve: CurvePoint[];
  drawdown_curve: CurvePoint[];
  benchmark_curve?: CurvePoint[];
  yearly_returns: YearlyReturn[];
  monthly_returns: MonthlyReturn[];
  trades: Trade[];
  status: 'pending' | 'running' | 'done' | 'failed';
  created_at: string;
}

export interface BacktestMetrics {
  total_return: number;
  ann_return: number;
  ann_volatility: number;
  sharpe: number;
  sortino: number;
  max_drawdown: number;
  calmar: number;
  win_rate: number;
  years: number;
  benchmark_return?: number;
  excess_return?: number;
  ann_excess?: number;
  profit_factor?: number;
  total_trades?: number;
}

export interface Trade {
  date: string;
  action: 'buy' | 'sell';
  price: number;
  quantity: number;
  pnl?: number;
}

export interface StockInfo {
  code: string;
  name: string;
  exchange: string;
  industry: string;
  market_cap: number;
  listed_date: string;
}

export interface KlineData {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface FinancialData {
  report_date: string;
  net_profit: number;
  revenue: number;
  eps: number;
  roe: number;
  debt_ratio: number;
  current_ratio: number;
  dividend_yield: number;
  pe: number;
  pb: number;
  gross_margin: number;
  net_margin: number;
}

export interface IndustryPeer {
  code: string;
  name: string;
  roe: number;
  gross_margin: number;
  debt_ratio: number;
  revenue_growth: number;
  net_profit_growth: number;
}

export interface IndustryComparison {
  industry: string;
  peers: IndustryPeer[];
}

export interface WatchlistItem {
  code: string;
  name: string;
  added_at: string | null;
  notes: string | null;
}

export interface Watchlist {
  id: number;
  name: string;
  stock_count: number;
  items: WatchlistItem[];
  created_at: string;
}

export interface QuoteItem {
  code: string;
  name: string;
  latest_price: number | null;
  change_pct: number | null;
  pe: number | null;
  pb: number | null;
  dividend_yield: number | null;
  notes: string | null;
  data_status: {
    has_daily: boolean;
    has_financial: boolean;
    daily_start: string | null;
    daily_end: string | null;
    financial_periods: number;
  } | null;
  data_freshness: string;
}

export interface WatchlistQuote {
  id: number;
  name: string;
  items: QuoteItem[];
}

export interface BatchPreviewItem {
  code: string;
  name: string;
  in_current: boolean;
  in_other: string[];
}

export interface BatchPreviewResponse {
  preview: BatchPreviewItem[];
  new_count: number;
  existing_count: number;
}

export interface StockSearchResult {
  code: string;
  name: string;
}

export interface NavItem {
  label: string;
  href: string;
  icon?: string;
}

export type ThemeMode = 'light' | 'dark' | 'system';

export type Freq = 'D' | 'W' | 'M' | 'Q' | 'Y' | '60min' | '30min' | '15min';

/** 分钟级频率列表 — 服务端直接获取，不需要客户端聚合 */
export const MINUTE_FREQS: Freq[] = ['60min', '30min', '15min'];

export function isMinuteFreq(freq: Freq): boolean {
  return (MINUTE_FREQS as string[]).includes(freq);
}

export interface IndicatorConfig {
  type: 'MA' | 'MACD' | 'RSI' | 'BOLL' | 'DONCHIAN';
  visible: boolean;
  params?: Record<string, number>;
}

export interface DateRange {
  start: string;
  end: string;
}

// ── Data Management ──────────────────────────────

export interface CacheStats {
  stock_count: number;
  total_rows: number;
  storage_bytes: number;
  date_range_start: string | null;
  date_range_end: string | null;
  freq_stats: Record<string, number>;
}

export interface DBStats {
  stock_count: number;
  financial_count: number;
  watchlist_count: number;
  strategy_count: number;
  backtest_count: number;
}

export interface DataStats {
  cache: CacheStats;
  database: DBStats;
}

export interface StockDataStatus {
  code: string;
  name: string;
  has_daily: boolean;
  daily_start: string | null;
  daily_end: string | null;
  daily_rows: number;
  has_financial: boolean;
  financial_start: string | null;
  financial_end: string | null;
  financial_rows: number;
  in_watchlist: string[];
}

export interface RefreshRequest {
  codes?: string[] | null;
  freq?: string;
  force?: boolean;
  discover_new?: boolean;
  max_new?: number;
}

export interface RefreshError {
  code: string;
  error: string;
}

export interface RefreshResult {
  updated: number;
  failed: number;
  new_discovered: number;
  errors: RefreshError[];
}

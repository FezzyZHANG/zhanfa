import axios from 'axios';
import type {
  Strategy,
  BacktestResult,
  BacktestMetrics,
  CurvePoint,
  YearlyReturn,
  MonthlyReturn,
  Trade,
  StockInfo,
  KlineData,
  FinancialData,
  Watchlist,
  WatchlistQuote,
  StockSearchResult,
  IndustryComparison,
  BatchPreviewResponse,
  DataStats,
  StockDataStatus,
  RefreshRequest,
  RefreshResult,
} from '@/types';
import {
  strategies as mockStrategies,
  backtestResults as mockBacktestResults,
  stocks as mockStocks,
  getKlineData as mockGetKline,
  financialData as mockFinancial,
  watchlists as mockWatchlists,
  getWatchlistQuotes as mockGetWatchlistQuotes,
  searchStocks as mockSearchStocks,
  industryComparison as mockIndustryComparison,
  dataStats as mockDataStats,
  stockDataStatusMap as mockStockDataStatusMap,
  mockRefreshData,
} from './mock';

const api = axios.create({
  baseURL: '/api',
  timeout: 30_000,
});

const USE_MOCK = import.meta.env.VITE_ENABLE_MOCK === 'true';

interface RequestOptions {
  signal?: AbortSignal;
}

interface ApiRequestConfig {
  params?: unknown;
  signal?: AbortSignal;
}

function signalConfig(options: RequestOptions): ApiRequestConfig | undefined {
  return options.signal ? { signal: options.signal } : undefined;
}

function paramsConfig(params: unknown, options: RequestOptions): ApiRequestConfig {
  return options.signal ? { params, signal: options.signal } : { params };
}

function apiGet<T>(url: string, config?: ApiRequestConfig) {
  return config ? api.get<T>(url, config) : api.get<T>(url);
}

function apiPost<T>(url: string, body?: unknown, config?: ApiRequestConfig) {
  if (config) return api.post<T>(url, body, config);
  return body === undefined ? api.post<T>(url) : api.post<T>(url, body);
}

function apiPut<T>(url: string, body: unknown, config?: ApiRequestConfig) {
  return config ? api.put<T>(url, body, config) : api.put<T>(url, body);
}

function apiDelete(url: string, config?: ApiRequestConfig) {
  return config ? api.delete(url, config) : api.delete(url);
}

function createAbortError(): Error {
  const error = new Error('Aborted');
  error.name = 'AbortError';
  return error;
}

function delay<T>(data: T, ms = 200, signal?: AbortSignal): Promise<T> {
  if (signal?.aborted) {
    return Promise.reject(createAbortError());
  }

  return new Promise((resolve, reject) => {
    const timer = window.setTimeout(() => resolve(data), ms);
    signal?.addEventListener(
      'abort',
      () => {
        window.clearTimeout(timer);
        reject(createAbortError());
      },
      { once: true },
    );
  });
}

// ── Strategies ──────────────────────────────────────

export async function fetchStrategies(params?: {
  category?: string;
  search?: string;
}, options: RequestOptions = {}): Promise<Strategy[]> {
  if (USE_MOCK) {
    let result = mockStrategies;
    if (params?.category) {
      result = result.filter((s) => s.category === params.category);
    }
    if (params?.search) {
      const kw = params.search.toLowerCase();
      result = result.filter(
        (s) =>
          s.name.toLowerCase().includes(kw) ||
          s.description.toLowerCase().includes(kw)
      );
    }
    return delay(result, 200, options.signal);
  }
  const { data } = await apiGet<Strategy[]>('/strategies', paramsConfig(params, options));
  return data;
}

export async function fetchStrategy(id: number, options: RequestOptions = {}): Promise<Strategy | undefined> {
  if (USE_MOCK) return delay(mockStrategies.find((s) => s.id === id), 200, options.signal);
  const { data } = await apiGet<Strategy>(`/strategies/${id}`, signalConfig(options));
  return data;
}

// ── Stocks ──────────────────────────────────────────

export async function fetchStocks(options: RequestOptions = {}): Promise<StockInfo[]> {
  if (USE_MOCK) return delay(mockStocks, 200, options.signal);
  const { data } = await apiGet<{ items: StockInfo[] }>('/stocks', paramsConfig({ page_size: 200 }, options));
  return data.items ?? [];
}

export async function fetchStock(code: string, options: RequestOptions = {}): Promise<StockInfo | undefined> {
  if (USE_MOCK) return delay(mockStocks.find((s) => s.code === code), 200, options.signal);
  const { data } = await apiGet<StockInfo>(`/stocks/${code}`, signalConfig(options));
  return data;
}

// ── K-line ──────────────────────────────────────────

export async function fetchKline(
  code: string,
  start?: string,
  end?: string,
  freq?: string,
  options: RequestOptions = {},
): Promise<KlineData[]> {
  if (USE_MOCK) return delay(mockGetKline(code, start, end), 300, options.signal);
  const params = freq === undefined ? { start, end } : { start, end, freq };
  const { data } = await apiGet<{ data: KlineData[] }>(
    `/stocks/${code}/daily`,
    paramsConfig(params, options),
  );
  return (data.data ?? []).map((d) => {
    const rawDate = typeof d.date === 'string' ? d.date : String(d.date);
    const dateStr = freq && !['daily', undefined].includes(freq)
      ? rawDate
      : rawDate.split('T')[0];
    return { ...d, date: dateStr };
  });
}

// ── Financial ───────────────────────────────────────

export async function fetchFinancials(code: string, options: RequestOptions = {}): Promise<FinancialData[]> {
  if (USE_MOCK) return delay(mockFinancial[code] || [], 200, options.signal);
  const { data } = await apiGet<{ data: FinancialData[] }>(
    `/stocks/${code}/financial`,
    signalConfig(options),
  );
  return data.data ?? [];
}

// ── Industry comparison ─────────────────────────────

export async function fetchIndustryComparison(
  industry: string,
  options: RequestOptions = {},
): Promise<IndustryComparison | undefined> {
  if (USE_MOCK) return delay(mockIndustryComparison[industry], 200, options.signal);
  const { data } = await apiGet<IndustryComparison>(
    `/stocks/industry/${encodeURIComponent(industry)}/comparison`,
    signalConfig(options),
  );
  return data;
}

// ── Watchlists ──────────────────────────────────────

export async function fetchWatchlists(options: RequestOptions = {}): Promise<Watchlist[]> {
  if (USE_MOCK) return delay(mockWatchlists, 200, options.signal);
  const { data } = await apiGet<Watchlist[]>('/watchlists', signalConfig(options));
  return data;
}

export async function createWatchlist(name: string, options: RequestOptions = {}): Promise<Watchlist> {
  if (USE_MOCK) {
    const wl: Watchlist = { id: Date.now(), name, stock_count: 0, items: [], created_at: new Date().toISOString() };
    return delay(wl, 200, options.signal);
  }
  const { data } = await apiPost<Watchlist>('/watchlists', { name }, signalConfig(options));
  return data;
}

export async function renameWatchlist(id: number, name: string, options: RequestOptions = {}): Promise<Watchlist> {
  if (USE_MOCK) return delay({ ...mockWatchlists.find((w) => w.id === id)!, name }, 200, options.signal);
  const { data } = await apiPut<Watchlist>(`/watchlists/${id}`, { name }, signalConfig(options));
  return data;
}

export async function deleteWatchlist(id: number, options: RequestOptions = {}): Promise<void> {
  if (USE_MOCK) return delay(undefined, 200, options.signal);
  await apiDelete(`/watchlists/${id}`, signalConfig(options));
}

export async function addToWatchlist(
  watchlistId: number,
  stockCode: string,
  notes?: string,
  options: RequestOptions = {},
): Promise<Watchlist> {
  if (USE_MOCK) return delay(mockWatchlists.find((w) => w.id === watchlistId)!, 200, options.signal);
  const body = notes === undefined ? { code: stockCode } : { code: stockCode, notes };
  const { data } = await apiPost<Watchlist>(
    `/watchlists/${watchlistId}/items`,
    body,
    signalConfig(options),
  );
  return data;
}

export async function removeFromWatchlist(
  watchlistId: number,
  stockCode: string,
  options: RequestOptions = {},
): Promise<void> {
  if (USE_MOCK) return delay(undefined, 200, options.signal);
  await apiDelete(`/watchlists/${watchlistId}/items/${stockCode}`, signalConfig(options));
}

export async function updateItemNotes(
  watchlistId: number,
  stockCode: string,
  notes: string | null,
  options: RequestOptions = {},
): Promise<Watchlist> {
  if (USE_MOCK) return delay(mockWatchlists.find((w) => w.id === watchlistId)!, 200, options.signal);
  const { data } = await apiPut<Watchlist>(
    `/watchlists/${watchlistId}/items/${stockCode}`,
    { notes },
    signalConfig(options),
  );
  return data;
}

export async function batchAddItems(
  watchlistId: number,
  codes: string[],
  options: RequestOptions = {},
): Promise<Watchlist> {
  if (USE_MOCK) return delay(mockWatchlists.find((w) => w.id === watchlistId)!, 200, options.signal);
  const { data } = await apiPost<Watchlist>(
    `/watchlists/${watchlistId}/items/batch`,
    { codes },
    signalConfig(options),
  );
  return data;
}

export async function batchMoveItems(
  fromWlId: number,
  toWlId: number,
  codes: string[],
  options: RequestOptions = {},
): Promise<Watchlist> {
  if (USE_MOCK) return delay(mockWatchlists.find((w) => w.id === fromWlId)!, 200, options.signal);
  const { data } = await apiPost<Watchlist>(
    `/watchlists/${fromWlId}/items/batch-move`,
    { target_watchlist_id: toWlId, codes },
    signalConfig(options),
  );
  return data;
}

export async function batchAddPreview(
  wlId: number,
  codes: string[],
  options: RequestOptions = {},
): Promise<BatchPreviewResponse> {
  if (USE_MOCK) {
    // Simple mock: mark all as new
    const wl = mockWatchlists.find((w) => w.id === wlId);
    const existing = new Set(wl?.items.map((i) => i.code) || []);
    return delay({
      preview: codes.map((code) => ({
        code,
        name: '',
        in_current: existing.has(code),
        in_other: [],
      })),
      new_count: codes.filter((c) => !existing.has(c)).length,
      existing_count: codes.filter((c) => existing.has(c)).length,
    }, 200, options.signal);
  }
  const { data } = await apiPost<BatchPreviewResponse>(
    `/watchlists/${wlId}/items/batch/preview`,
    { codes },
    signalConfig(options),
  );
  return data;
}

export async function batchDeleteItems(
  wlId: number,
  codes: string[],
  options: RequestOptions = {},
): Promise<void> {
  if (USE_MOCK) return delay(undefined, 200, options.signal);
  await apiPost(`/watchlists/${wlId}/items/batch-delete`, { codes }, signalConfig(options));
}

export async function fetchWatchlistQuotes(wlId: number, options: RequestOptions = {}): Promise<WatchlistQuote> {
  if (USE_MOCK) return delay(mockGetWatchlistQuotes(wlId), 300, options.signal);
  const { data } = await apiGet<WatchlistQuote>(`/watchlists/${wlId}/quotes`, signalConfig(options));
  return data;
}

export async function searchStocks(q: string, options: RequestOptions = {}): Promise<StockSearchResult[]> {
  if (USE_MOCK) return delay(mockSearchStocks(q), 150, options.signal);
  const { data } = await apiGet<StockSearchResult[]>('/watchlists/search', paramsConfig({ q }, options));
  return data;
}

export function getExportCsvUrl(wlId: number): string {
  return `/api/watchlists/${wlId}/export`;
}

// ── Backtest ────────────────────────────────────────

function mapBacktestStatus(status: string): BacktestResult['status'] {
  if (status === 'completed') return 'done';
  if (status === 'pending' || status === 'running' || status === 'failed') return status;
  console.warn(`Unknown backtest status: ${status}`);
  return 'pending';
}

// ── Shared BacktestResult builders ──────────────────

interface BacktestResultInput {
  id: string;
  strategy_id?: number;
  strategy_name?: string;
  stock_codes?: string[];
  params?: Record<string, unknown>;
  start_date?: string;
  end_date?: string;
  metrics?: Record<string, number> | null;
  equity_curve?: CurvePoint[] | null;
  drawdown_curve?: CurvePoint[] | null;
  benchmark_curve?: CurvePoint[] | null;
  yearly_returns?: YearlyReturn[] | null;
  monthly_returns?: MonthlyReturn[] | null;
  trades?: { date: string; action: string; price: number; quantity: number; pnl?: number }[] | null;
  status: string;
  created_at?: string;
}

function emptyBacktestMetrics(): BacktestMetrics {
  return {
    total_return: 0,
    ann_return: 0,
    ann_volatility: 0,
    sharpe: 0,
    sortino: 0,
    max_drawdown: 0,
    calmar: 0,
    win_rate: 0,
    years: 0,
  };
}

function mapTrades(
  trades: { date: string; action: string; price: number; quantity: number; pnl?: number }[] | null | undefined
): Trade[] {
  if (!trades || trades.length === 0) return [];
  return trades.map((t) => ({
    date: t.date,
    action: t.action as 'buy' | 'sell',
    price: t.price,
    quantity: t.quantity,
    pnl: t.pnl,
  }));
}

function buildBacktestResult(input: BacktestResultInput): BacktestResult {
  const m = input.metrics || {};
  return {
    id: input.id,
    strategy_id: input.strategy_id ?? 0,
    strategy_name: input.strategy_name,
    stock_codes: input.stock_codes ?? [],
    params: input.params ?? {},
    start_date: input.start_date ?? '',
    end_date: input.end_date ?? '',
    metrics: {
      ...emptyBacktestMetrics(),
      total_return: m.total_return ?? 0,
      ann_return: m.ann_return ?? 0,
      ann_volatility: m.ann_volatility ?? 0,
      sharpe: m.sharpe ?? 0,
      sortino: m.sortino ?? 0,
      max_drawdown: m.max_drawdown ?? 0,
      calmar: m.calmar ?? 0,
      win_rate: m.win_rate ?? 0,
      years: m.years ?? 0,
    },
    equity_curve: input.equity_curve ?? [],
    drawdown_curve: input.drawdown_curve ?? [],
    benchmark_curve: input.benchmark_curve ?? undefined,
    yearly_returns: input.yearly_returns ?? [],
    monthly_returns: input.monthly_returns ?? [],
    trades: mapTrades(input.trades),
    status: mapBacktestStatus(input.status),
    created_at: input.created_at ?? '',
  };
}

// ── Backend BacktestResult shapes ────────────────────────

/** GET /api/backtest/history returns compact rows for list views. */
interface BacktestHistoryItem {
  task_id: string;
  code: string;
  strategy: string;
  status: string;
  total_return: number | null;
  sharpe: number | null;
  max_drawdown: number | null;
  created_at: string;
}

/** GET /api/backtest/:task_id returns the full async task payload. */
interface BackendBacktestResult {
  task_id: string;
  status: string;
  request: {
    code: string;
    strategy: string;
    start_date: string;
    end_date: string;
    initial_capital: number;
    strategy_id?: number;
    params: Record<string, unknown>;
  } | null;
  metrics: Record<string, number> | null;
  equity_curve: CurvePoint[] | null;
  drawdown_curve: CurvePoint[] | null;
  benchmark_curve: CurvePoint[] | null;
  yearly_returns: YearlyReturn[] | null;
  monthly_returns: MonthlyReturn[] | null;
  trades: { date: string; action: string; price: number; quantity: number; pnl?: number }[] | null;
  error: string | null;
  created_at: string;
  completed_at: string | null;
}

/** GET /api/strategies/:id/results returns persisted result rows for one strategy. */
interface StrategyBacktestResult {
  id: string;
  db_id: number;
  strategy_id: number;
  stock_codes: string[];
  params: Record<string, unknown>;
  start_date: string;
  end_date: string;
  metrics: Record<string, number> | null;
  equity_curve: CurvePoint[] | null;
  drawdown_curve: CurvePoint[] | null;
  benchmark_curve: CurvePoint[] | null;
  yearly_returns: YearlyReturn[] | null;
  monthly_returns: MonthlyReturn[] | null;
  trades: { date: string; action: string; price: number; quantity: number; pnl?: number }[] | null;
  status: string;
  created_at: string;
}

type BackendBacktestShape = BacktestHistoryItem | BackendBacktestResult | StrategyBacktestResult;

function isTaskResult(raw: Partial<BackendBacktestShape>): raw is BackendBacktestResult {
  return 'task_id' in raw && 'request' in raw;
}

function isHistoryItem(raw: Partial<BackendBacktestShape>): raw is BacktestHistoryItem {
  return 'task_id' in raw && 'code' in raw && 'strategy' in raw;
}

function normalizeBacktestResult(raw: unknown): BacktestResult {
  const item = raw as Partial<BackendBacktestShape>;

  if (isTaskResult(item)) {
    const req = item.request;
    return buildBacktestResult({
      id: item.task_id,
      strategy_id: req?.strategy_id ?? 0,
      strategy_name: req?.strategy || '',
      stock_codes: req ? [req.code] : [],
      params: req?.params,
      start_date: req?.start_date,
      end_date: req?.end_date,
      metrics: item.metrics,
      equity_curve: item.equity_curve,
      drawdown_curve: item.drawdown_curve,
      benchmark_curve: item.benchmark_curve,
      yearly_returns: item.yearly_returns,
      monthly_returns: item.monthly_returns,
      trades: item.trades,
      status: item.status,
      created_at: item.created_at,
    });
  }

  if (isHistoryItem(item)) {
    return buildBacktestResult({
      id: item.task_id,
      strategy_name: item.strategy,
      stock_codes: [item.code],
      metrics: {
        total_return: item.total_return ?? 0,
        sharpe: item.sharpe ?? 0,
        max_drawdown: item.max_drawdown ?? 0,
      },
      status: item.status,
      created_at: item.created_at,
    });
  }

  const strategyResult = item as StrategyBacktestResult;
  return buildBacktestResult({
    id: strategyResult.id,
    strategy_id: strategyResult.strategy_id,
    stock_codes: strategyResult.stock_codes,
    params: strategyResult.params,
    start_date: strategyResult.start_date,
    end_date: strategyResult.end_date,
    metrics: strategyResult.metrics,
    equity_curve: strategyResult.equity_curve,
    drawdown_curve: strategyResult.drawdown_curve,
    benchmark_curve: strategyResult.benchmark_curve,
    yearly_returns: strategyResult.yearly_returns,
    monthly_returns: strategyResult.monthly_returns,
    trades: strategyResult.trades,
    status: strategyResult.status,
    created_at: strategyResult.created_at,
  });
}

export async function fetchBacktestResults(
  strategyId?: number,
  options: RequestOptions = {},
): Promise<BacktestResult[]> {
  if (USE_MOCK) {
    return delay(
      strategyId
        ? mockBacktestResults.filter((r) => r.strategy_id === strategyId)
        : mockBacktestResults,
      200,
      options.signal,
    );
  }
  if (strategyId !== undefined) {
    const { data } = await apiGet<StrategyBacktestResult[]>(
      `/strategies/${strategyId}/results`,
      signalConfig(options),
    );
    return (data ?? []).map(normalizeBacktestResult);
  }
  const { data } = await apiGet<BacktestHistoryItem[]>('/backtest/history', signalConfig(options));
  return (data ?? []).map(normalizeBacktestResult);
}

export async function fetchBacktestResult(
  id: number | string,
  options: RequestOptions = {},
): Promise<BacktestResult | undefined> {
  const taskId = String(id);
  if (USE_MOCK) return delay(mockBacktestResults.find((r) => String(r.id) === taskId), 200, options.signal);
  const { data } = await apiGet<BackendBacktestResult>(`/backtest/${taskId}`, signalConfig(options));
  return normalizeBacktestResult(data);
}

export async function submitBacktest(body: {
  strategy_id: number;
  code: string;
  strategy: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  params: Record<string, string>;
}, options: RequestOptions = {}): Promise<{ task_id: string }> {
  if (USE_MOCK) {
    const taskId = Math.random().toString(36).slice(2, 10);
    return delay({ task_id: taskId }, 500, options.signal);
  }
  const payload = {
    ...body,
    strategy_id: body.strategy_id,
    commission: 0.0005,
    slippage: 0.001,
    start_date: body.start_date,
    end_date: body.end_date,
  };
  const { data } = await apiPost<{ task_id: string }>('/backtest/run', payload, signalConfig(options));
  return data;
}

export async function getBacktestTask(taskId: string, options: RequestOptions = {}): Promise<BacktestResult | undefined> {
  if (USE_MOCK) {
    const idx = parseInt(taskId, 36) % mockBacktestResults.length;
    return delay(mockBacktestResults[isNaN(idx) ? 0 : idx], 300, options.signal);
  }
  const { data } = await apiGet<BackendBacktestResult>(`/backtest/${taskId}`, signalConfig(options));
  return normalizeBacktestResult(data);
}

export async function fetchBacktestCompare(
  strategyIds: number[],
  options: RequestOptions = {},
): Promise<BacktestResult[]> {
  if (USE_MOCK) {
    return delay(mockBacktestResults.filter((r) => strategyIds.includes(r.strategy_id)), 200, options.signal);
  }
  // No backend endpoint yet (TICKET-012)
  return [];
}

// ── Data Management ───────────────────────────────

export async function initializeData(options: RequestOptions = {}): Promise<{ stock_count: number; message: string }> {
  const { data } = await apiPost<{ stock_count: number; message: string }>(
    '/data/initialize',
    undefined,
    signalConfig(options),
  );
  return data;
}

export async function fetchDataStats(options: RequestOptions = {}): Promise<DataStats> {
  if (USE_MOCK) return delay(mockDataStats, 100, options.signal);
  const { data } = await apiGet<DataStats>('/data/stats', signalConfig(options));
  return data;
}

export async function fetchStockDataStatus(
  code: string,
  options: RequestOptions = {},
): Promise<StockDataStatus | undefined> {
  if (USE_MOCK) return delay(mockStockDataStatusMap[code], 150, options.signal);
  const { data } = await apiGet<StockDataStatus>('/data/stock-status', paramsConfig({ code }, options));
  return data;
}

export async function refreshData(body: RefreshRequest, options: RequestOptions = {}): Promise<RefreshResult> {
  if (USE_MOCK) return delay(mockRefreshData(body.codes, body.force), 2000, options.signal);
  const { data } = await apiPost<RefreshResult>('/data/refresh', body, signalConfig(options));
  return data;
}

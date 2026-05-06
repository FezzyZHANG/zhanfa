import axios from 'axios';
import type {
  Strategy,
  BacktestResult,
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

function delay<T>(data: T, ms = 200): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(data), ms));
}

// ── Strategies ──────────────────────────────────────

export async function fetchStrategies(params?: {
  category?: string;
  search?: string;
}): Promise<Strategy[]> {
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
    return delay(result);
  }
  const { data } = await api.get<Strategy[]>('/strategies', { params });
  return data;
}

export async function fetchStrategy(id: number): Promise<Strategy | undefined> {
  if (USE_MOCK) return delay(mockStrategies.find((s) => s.id === id));
  const { data } = await api.get<Strategy>(`/strategies/${id}`);
  return data;
}

// ── Stocks ──────────────────────────────────────────

export async function fetchStocks(): Promise<StockInfo[]> {
  if (USE_MOCK) return delay(mockStocks);
  const { data } = await api.get<{ items: StockInfo[] }>('/stocks', {
    params: { page_size: 200 },
  });
  return data.items ?? [];
}

export async function fetchStock(code: string): Promise<StockInfo | undefined> {
  if (USE_MOCK) return delay(mockStocks.find((s) => s.code === code));
  const { data } = await api.get<StockInfo>(`/stocks/${code}`);
  return data;
}

// ── K-line ──────────────────────────────────────────

export async function fetchKline(
  code: string,
  start?: string,
  end?: string,
  freq?: string,
): Promise<KlineData[]> {
  if (USE_MOCK) return delay(mockGetKline(code, start, end), 300);
  const { data } = await api.get<{ data: KlineData[] }>(
    `/stocks/${code}/daily`,
    { params: { start, end, freq } },
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

export async function fetchFinancials(code: string): Promise<FinancialData[]> {
  if (USE_MOCK) return delay(mockFinancial[code] || []);
  const { data } = await api.get<{ data: FinancialData[] }>(`/stocks/${code}/financial`);
  return data.data ?? [];
}

// ── Industry comparison ─────────────────────────────

export async function fetchIndustryComparison(industry: string): Promise<IndustryComparison | undefined> {
  if (USE_MOCK) return delay(mockIndustryComparison[industry]);
  const { data } = await api.get<IndustryComparison>(
    `/stocks/industry/${encodeURIComponent(industry)}/comparison`
  );
  return data;
}

// ── Watchlists ──────────────────────────────────────

export async function fetchWatchlists(): Promise<Watchlist[]> {
  if (USE_MOCK) return delay(mockWatchlists);
  const { data } = await api.get<Watchlist[]>('/watchlists');
  return data;
}

export async function createWatchlist(name: string): Promise<Watchlist> {
  if (USE_MOCK) {
    const wl: Watchlist = { id: Date.now(), name, stock_count: 0, items: [], created_at: new Date().toISOString() };
    return delay(wl);
  }
  const { data } = await api.post<Watchlist>('/watchlists', { name });
  return data;
}

export async function renameWatchlist(id: number, name: string): Promise<Watchlist> {
  if (USE_MOCK) return delay({ ...mockWatchlists.find((w) => w.id === id)!, name });
  const { data } = await api.put<Watchlist>(`/watchlists/${id}`, { name });
  return data;
}

export async function deleteWatchlist(id: number): Promise<void> {
  if (USE_MOCK) return delay(undefined);
  await api.delete(`/watchlists/${id}`);
}

export async function addToWatchlist(
  watchlistId: number,
  stockCode: string,
  notes?: string
): Promise<Watchlist> {
  if (USE_MOCK) return delay(mockWatchlists.find((w) => w.id === watchlistId)!);
  const { data } = await api.post<Watchlist>(`/watchlists/${watchlistId}/items`, { code: stockCode, notes });
  return data;
}

export async function removeFromWatchlist(
  watchlistId: number,
  stockCode: string
): Promise<void> {
  if (USE_MOCK) return delay(undefined);
  await api.delete(`/watchlists/${watchlistId}/items/${stockCode}`);
}

export async function updateItemNotes(
  watchlistId: number,
  stockCode: string,
  notes: string | null
): Promise<Watchlist> {
  if (USE_MOCK) return delay(mockWatchlists.find((w) => w.id === watchlistId)!);
  const { data } = await api.put<Watchlist>(`/watchlists/${watchlistId}/items/${stockCode}`, { notes });
  return data;
}

export async function batchAddItems(
  watchlistId: number,
  codes: string[]
): Promise<Watchlist> {
  if (USE_MOCK) return delay(mockWatchlists.find((w) => w.id === watchlistId)!);
  const { data } = await api.post<Watchlist>(`/watchlists/${watchlistId}/items/batch`, { codes });
  return data;
}

export async function batchMoveItems(
  fromWlId: number,
  toWlId: number,
  codes: string[]
): Promise<Watchlist> {
  if (USE_MOCK) return delay(mockWatchlists.find((w) => w.id === fromWlId)!);
  const { data } = await api.post<Watchlist>(`/watchlists/${fromWlId}/items/batch-move`, { target_watchlist_id: toWlId, codes });
  return data;
}

export async function batchAddPreview(wlId: number, codes: string[]): Promise<BatchPreviewResponse> {
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
    });
  }
  const { data } = await api.post<BatchPreviewResponse>(`/watchlists/${wlId}/items/batch/preview`, { codes });
  return data;
}

export async function batchDeleteItems(wlId: number, codes: string[]): Promise<void> {
  if (USE_MOCK) return delay(undefined);
  await api.post(`/watchlists/${wlId}/items/batch-delete`, { codes });
}

export async function fetchWatchlistQuotes(wlId: number): Promise<WatchlistQuote> {
  if (USE_MOCK) return delay(mockGetWatchlistQuotes(wlId), 300);
  const { data } = await api.get<WatchlistQuote>(`/watchlists/${wlId}/quotes`);
  return data;
}

export async function searchStocks(q: string): Promise<StockSearchResult[]> {
  if (USE_MOCK) return delay(mockSearchStocks(q), 150);
  const { data } = await api.get<StockSearchResult[]>('/watchlists/search', { params: { q } });
  return data;
}

export function getExportCsvUrl(wlId: number): string {
  return `/api/watchlists/${wlId}/export`;
}

// ── Backtest ────────────────────────────────────────

function mapBacktestStatus(status: string): BacktestResult['status'] {
  if (status === 'completed') return 'done';
  if (status === 'pending' || status === 'running' || status === 'failed') return status;
  return 'pending';
}

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

function historyItemToResult(item: BacktestHistoryItem): BacktestResult {
  return {
    id: item.task_id,
    strategy_id: 0,
    strategy_name: item.strategy,
    stock_codes: [item.code],
    params: {},
    start_date: '',
    end_date: '',
    metrics: {
      total_return: item.total_return ?? 0,
      ann_return: 0,
      ann_volatility: 0,
      sharpe: item.sharpe ?? 0,
      sortino: 0,
      max_drawdown: item.max_drawdown ?? 0,
      calmar: 0,
      win_rate: 0,
      years: 0,
    },
    equity_curve: [],
    drawdown_curve: [],
    yearly_returns: [],
    monthly_returns: [],
    trades: [],
    status: mapBacktestStatus(item.status),
    created_at: item.created_at,
  };
}

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
  equity_curve: { date: string; value: number }[] | null;
  drawdown_curve: { date: string; value: number }[] | null;
  benchmark_curve: { date: string; value: number }[] | null;
  yearly_returns: { year: number; value: number }[] | null;
  monthly_returns: { year: number; month: number; value: number }[] | null;
  trades: { date: string; action: string; price: number; quantity: number; pnl?: number }[] | null;
  error: string | null;
  created_at: string;
  completed_at: string | null;
}

function taskToResult(task: BackendBacktestResult): BacktestResult {
  const m = task.metrics || {};
  const req = task.request;
  return {
    id: task.task_id,
    strategy_id: req?.strategy_id ?? 0,
    strategy_name: req?.strategy || '',
    stock_codes: req ? [req.code] : [],
    params: req?.params || {},
    start_date: req?.start_date || '',
    end_date: req?.end_date || '',
    benchmark_curve: task.benchmark_curve ?? undefined,
    metrics: {
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
    equity_curve: task.equity_curve ?? [],
    drawdown_curve: task.drawdown_curve ?? [],
    yearly_returns: task.yearly_returns ?? [],
    monthly_returns: task.monthly_returns ?? [],
    trades: (task.trades ?? []).map((t) => ({
      date: t.date,
      action: t.action as 'buy' | 'sell',
      price: t.price,
      quantity: t.quantity,
      pnl: t.pnl,
    })),
    status: mapBacktestStatus(task.status),
    created_at: task.created_at,
  };
}

interface StrategyBacktestResult {
  id: string;
  db_id: number;
  strategy_id: number;
  stock_codes: string[];
  params: Record<string, unknown>;
  start_date: string;
  end_date: string;
  metrics: Record<string, number> | null;
  equity_curve: { date: string; value: number }[] | null;
  drawdown_curve: { date: string; value: number }[] | null;
  benchmark_curve: { date: string; value: number }[] | null;
  yearly_returns: { year: number; value: number }[] | null;
  monthly_returns: { year: number; month: number; value: number }[] | null;
  trades: { date: string; action: string; price: number; quantity: number; pnl?: number }[] | null;
  status: string;
  created_at: string;
}

function strategyResultToBacktestResult(item: StrategyBacktestResult): BacktestResult {
  const m = item.metrics || {};
  return {
    id: item.id,
    strategy_id: item.strategy_id,
    stock_codes: item.stock_codes || [],
    params: item.params || {},
    start_date: item.start_date || '',
    end_date: item.end_date || '',
    metrics: {
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
    equity_curve: item.equity_curve ?? [],
    drawdown_curve: item.drawdown_curve ?? [],
    benchmark_curve: item.benchmark_curve ?? undefined,
    yearly_returns: item.yearly_returns ?? [],
    monthly_returns: item.monthly_returns ?? [],
    trades: (item.trades ?? []).map((t) => ({
      date: t.date,
      action: t.action as 'buy' | 'sell',
      price: t.price,
      quantity: t.quantity,
      pnl: t.pnl,
    })),
    status: mapBacktestStatus(item.status),
    created_at: item.created_at || '',
  };
}

export async function fetchBacktestResults(
  strategyId?: number
): Promise<BacktestResult[]> {
  if (USE_MOCK) {
    return delay(
      strategyId
        ? mockBacktestResults.filter((r) => r.strategy_id === strategyId)
        : mockBacktestResults
    );
  }
  if (strategyId !== undefined) {
    const { data } = await api.get<StrategyBacktestResult[]>(`/strategies/${strategyId}/results`);
    return (data ?? []).map(strategyResultToBacktestResult);
  }
  const { data } = await api.get<BacktestHistoryItem[]>('/backtest/history');
  return (data ?? []).map(historyItemToResult);
}

export async function fetchBacktestResult(
  id: number | string
): Promise<BacktestResult | undefined> {
  const taskId = String(id);
  if (USE_MOCK) return delay(mockBacktestResults.find((r) => String(r.id) === taskId));
  const { data } = await api.get<BackendBacktestResult>(`/backtest/${taskId}`);
  return taskToResult(data);
}

export async function submitBacktest(body: {
  strategy_id: number;
  code: string;
  strategy: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  params: Record<string, string>;
}): Promise<{ task_id: string }> {
  if (USE_MOCK) {
    const taskId = Math.random().toString(36).slice(2, 10);
    return delay({ task_id: taskId }, 500);
  }
  const payload = {
    ...body,
    strategy_id: body.strategy_id,
    commission: 0.0005,
    slippage: 0.001,
    start_date: body.start_date.replace(/-/g, ''),
    end_date: body.end_date.replace(/-/g, ''),
  };
  const { data } = await api.post<{ task_id: string }>('/backtest/run', payload);
  return data;
}

export async function getBacktestTask(taskId: string): Promise<BacktestResult | undefined> {
  if (USE_MOCK) {
    const idx = parseInt(taskId, 36) % mockBacktestResults.length;
    return delay(mockBacktestResults[isNaN(idx) ? 0 : idx], 300);
  }
  const { data } = await api.get<BackendBacktestResult>(`/backtest/${taskId}`);
  return taskToResult(data);
}

export async function fetchBacktestCompare(strategyIds: number[]): Promise<BacktestResult[]> {
  if (USE_MOCK) {
    return delay(mockBacktestResults.filter((r) => strategyIds.includes(r.strategy_id)));
  }
  // No backend endpoint yet (TICKET-012)
  return [];
}

// ── Data Management ───────────────────────────────

export async function initializeData(): Promise<{ stock_count: number; message: string }> {
  const { data } = await api.post<{ stock_count: number; message: string }>('/data/initialize');
  return data;
}

export async function fetchDataStats(): Promise<DataStats> {
  if (USE_MOCK) return delay(mockDataStats, 100);
  const { data } = await api.get<DataStats>('/data/stats');
  return data;
}

export async function fetchStockDataStatus(code: string): Promise<StockDataStatus | undefined> {
  if (USE_MOCK) return delay(mockStockDataStatusMap[code], 150);
  const { data } = await api.get<StockDataStatus>('/data/stock-status', { params: { code } });
  return data;
}

export async function refreshData(body: RefreshRequest): Promise<RefreshResult> {
  if (USE_MOCK) return delay(mockRefreshData(body.codes, body.force), 2000);
  const { data } = await api.post<RefreshResult>('/data/refresh', body);
  return data;
}

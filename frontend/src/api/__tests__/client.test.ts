import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { Strategy, StockInfo, KlineData } from '@/types';

const { mockGet, mockPost, mockPut, mockDelete } = vi.hoisted(() => ({
  mockGet: vi.fn(),
  mockPost: vi.fn(),
  mockPut: vi.fn(),
  mockDelete: vi.fn(),
}));

vi.mock('axios', () => ({
  default: {
    create: () => ({
      get: mockGet,
      post: mockPost,
      put: mockPut,
      delete: mockDelete,
    }),
  },
}));

import {
  fetchStrategies,
  fetchStrategy,
  fetchStocks,
  fetchStock,
  fetchKline,
  fetchFinancials,
  fetchWatchlists,
  createWatchlist,
  deleteWatchlist,
  fetchWatchlistQuotes,
  searchStocks,
  getExportCsvUrl,
  submitBacktest,
  fetchBacktestResults,
  fetchBacktestResult,
  fetchIndustryComparison,
  addToWatchlist,
  removeFromWatchlist,
  batchAddItems,
} from '@/api/client';

beforeEach(() => {
  vi.clearAllMocks();
});

// ── Strategies ──────────────────────────────────────

describe('fetchStrategies', () => {
  it('calls GET /strategies', async () => {
    const items: Strategy[] = [{
      id: 1, name: 'Test', category: 'trend', description: 'desc',
      params: {}, created_at: '', updated_at: '',
    }];
    mockGet.mockResolvedValueOnce({ data: items });
    const result = await fetchStrategies();
    expect(mockGet).toHaveBeenCalledWith('/strategies', { params: undefined });
    expect(result).toEqual(items);
  });

  it('passes query params', async () => {
    mockGet.mockResolvedValueOnce({ data: [] });
    await fetchStrategies({ category: 'trend', search: 'test' });
    expect(mockGet).toHaveBeenCalledWith('/strategies', {
      params: { category: 'trend', search: 'test' },
    });
  });
});

describe('fetchStrategy', () => {
  it('calls GET /strategies/:id', async () => {
    const strategy: Strategy = {
      id: 1, name: 'Test', category: 'trend', description: 'desc',
      params: {}, created_at: '', updated_at: '',
    };
    mockGet.mockResolvedValueOnce({ data: strategy });
    const result = await fetchStrategy(1);
    expect(mockGet).toHaveBeenCalledWith('/strategies/1');
    expect(result).toEqual(strategy);
  });
});

// ── Stocks ──────────────────────────────────────────

describe('fetchStocks', () => {
  it('calls GET /stocks', async () => {
    const items: StockInfo[] = [
      { code: '000001', name: 'Test', exchange: '', industry: '', market_cap: 0, listed_date: '' },
    ];
    mockGet.mockResolvedValueOnce({ data: { items } });
    const result = await fetchStocks();
    expect(mockGet).toHaveBeenCalledWith('/stocks', { params: { page_size: 200 } });
    expect(result).toEqual(items);
  });

  it('handles missing items', async () => {
    mockGet.mockResolvedValueOnce({ data: {} });
    const result = await fetchStocks();
    expect(result).toEqual([]);
  });
});

describe('fetchStock', () => {
  it('calls GET /stocks/:code', async () => {
    mockGet.mockResolvedValueOnce({
      data: { code: '000001', name: 'Test' },
    });
    const result = await fetchStock('000001');
    expect(mockGet).toHaveBeenCalledWith('/stocks/000001');
    expect(result).toEqual({
      code: '000001', name: 'Test', exchange: '', industry: '', market_cap: 0, listed_date: '',
    });
  });
});

// ── K-line ──────────────────────────────────────────

describe('fetchKline', () => {
  it('calls GET /stocks/:code/daily', async () => {
    const klineData: KlineData[] = [
      { date: '2024-01-01', open: 10, high: 11, low: 9, close: 10.5, volume: 1000 },
    ];
    mockGet.mockResolvedValueOnce({ data: { data: klineData } });
    const result = await fetchKline('000001', '2024-01-01', '2024-12-31');
    expect(mockGet).toHaveBeenCalledWith('/stocks/000001/daily', {
      params: { start: '2024-01-01', end: '2024-12-31' },
    });
    expect(result).toEqual(klineData);
  });

  it('strips time from date strings', async () => {
    mockGet.mockResolvedValueOnce({
      data: { data: [{ date: '2024-01-01T00:00:00', open: 10, high: 11, low: 9, close: 10.5, volume: 1000 }] },
    });
    const result = await fetchKline('000001');
    expect(result[0].date).toBe('2024-01-01');
  });
});

// ── Financial ───────────────────────────────────────

describe('fetchFinancials', () => {
  it('calls GET /stocks/:code/financial', async () => {
    mockGet.mockResolvedValueOnce({ data: { data: [] } });
    const result = await fetchFinancials('000001');
    expect(mockGet).toHaveBeenCalledWith('/stocks/000001/financial');
    expect(result).toEqual([]);
  });
});

// ── Industry Comparison ────────────────────────────

describe('fetchIndustryComparison', () => {
  const mockPeers = [
    { code: '600519', name: '贵州茅台', roe: 0.294, gross_margin: 0.918, debt_ratio: 0.192, revenue_growth: 0.138, net_profit_growth: 0.144 },
    { code: '000858', name: '五粮液', roe: 0.238, gross_margin: 0.752, debt_ratio: 0.201, revenue_growth: 0.117, net_profit_growth: 0.122 },
  ];

  it('calls GET /stocks/industry/:industry/comparison', async () => {
    mockGet.mockResolvedValueOnce({
      data: { industry: '白酒', peers: mockPeers },
    });
    const result = await fetchIndustryComparison('白酒');
    expect(mockGet).toHaveBeenCalledWith('/stocks/industry/%E7%99%BD%E9%85%92/comparison');
    expect(result).toEqual({ industry: '白酒', peers: mockPeers });
  });

  it('URL-encodes industry name with special characters', async () => {
    mockGet.mockResolvedValueOnce({ data: { industry: '医 药', peers: [] } });
    await fetchIndustryComparison('医 药');
    expect(mockGet).toHaveBeenCalledWith('/stocks/industry/%E5%8C%BB%20%E8%8D%AF/comparison');
  });

  it('handles empty peers array', async () => {
    mockGet.mockResolvedValueOnce({ data: { industry: '未知行业', peers: [] } });
    const result = await fetchIndustryComparison('未知行业');
    expect(result).toEqual({ industry: '未知行业', peers: [] });
  });
});

// ── Watchlists ──────────────────────────────────────

describe('fetchWatchlists', () => {
  it('calls GET /watchlists', async () => {
    mockGet.mockResolvedValueOnce({ data: [] });
    const result = await fetchWatchlists();
    expect(mockGet).toHaveBeenCalledWith('/watchlists');
    expect(result).toEqual([]);
  });
});

describe('createWatchlist', () => {
  it('calls POST /watchlists', async () => {
    mockPost.mockResolvedValueOnce({ data: { id: 1, name: 'New' } });
    await createWatchlist('New');
    expect(mockPost).toHaveBeenCalledWith('/watchlists', { name: 'New' });
  });
});

describe('deleteWatchlist', () => {
  it('calls DELETE /watchlists/:id', async () => {
    mockDelete.mockResolvedValueOnce({});
    await deleteWatchlist(1);
    expect(mockDelete).toHaveBeenCalledWith('/watchlists/1');
  });
});

describe('fetchWatchlistQuotes', () => {
  it('calls GET /watchlists/:id/quotes', async () => {
    mockGet.mockResolvedValueOnce({ data: { id: 1, name: 'WL', items: [] } });
    const result = await fetchWatchlistQuotes(1);
    expect(mockGet).toHaveBeenCalledWith('/watchlists/1/quotes');
    expect(result).toEqual({ id: 1, name: 'WL', items: [] });
  });
});

describe('searchStocks', () => {
  it('calls GET /watchlists/search', async () => {
    mockGet.mockResolvedValueOnce({ data: [] });
    await searchStocks('茅台');
    expect(mockGet).toHaveBeenCalledWith('/watchlists/search', { params: { q: '茅台' } });
  });
});

// ── Export URL ──────────────────────────────────────

describe('getExportCsvUrl', () => {
  it('returns export URL', () => {
    expect(getExportCsvUrl(5)).toBe('/api/watchlists/5/export');
  });
});

// ── Watchlist Quotes Mapping ────────────────────────

describe('fetchWatchlistQuotes field mapping', () => {
  const mockQuoteItem = {
    code: '000001',
    name: '平安银行',
    latest_price: 12.5,
    change_pct: 0.025,
    pe: 6.8,
    pb: 0.9,
    dividend_yield: 0.035,
    notes: '银行龙头',
    data_status: {
      has_daily: true,
      has_financial: true,
      daily_start: '2024-01-01',
      daily_end: '2025-12-31',
      financial_periods: 8,
    },
    data_freshness: 'cached',
  };

  it('passes data_freshness through', async () => {
    mockGet.mockResolvedValueOnce({
      data: { id: 1, name: 'WL', items: [mockQuoteItem] },
    });
    const result = await fetchWatchlistQuotes(1);
    expect(result.items[0].data_freshness).toBe('cached');
  });

  it('passes data_status sub-fields through', async () => {
    mockGet.mockResolvedValueOnce({
      data: { id: 1, name: 'WL', items: [mockQuoteItem] },
    });
    const result = await fetchWatchlistQuotes(1);
    expect(result.items[0].data_status).toEqual({
      has_daily: true,
      has_financial: true,
      daily_start: '2024-01-01',
      daily_end: '2025-12-31',
      financial_periods: 8,
    });
  });

  it('passes notes field through', async () => {
    mockGet.mockResolvedValueOnce({
      data: { id: 1, name: 'WL', items: [mockQuoteItem] },
    });
    const result = await fetchWatchlistQuotes(1);
    expect(result.items[0].notes).toBe('银行龙头');
  });

  it('handles empty items array', async () => {
    mockGet.mockResolvedValueOnce({
      data: { id: 1, name: 'WL', items: [] },
    });
    const result = await fetchWatchlistQuotes(1);
    expect(result.items).toEqual([]);
  });
});

// ── Watchlist Items CRUD ────────────────────────────

describe('addToWatchlist', () => {
  it('calls POST /watchlists/:id/items with code', async () => {
    mockPost.mockResolvedValueOnce({
      data: { id: 1, name: 'WL', stock_count: 1, items: [] },
    });
    await addToWatchlist(1, '000001');
    expect(mockPost).toHaveBeenCalledWith('/watchlists/1/items', { code: '000001' });
  });

  it('passes notes when provided', async () => {
    mockPost.mockResolvedValueOnce({
      data: { id: 1, name: 'WL', stock_count: 1, items: [] },
    });
    await addToWatchlist(1, '000001', '重点观察');
    expect(mockPost).toHaveBeenCalledWith('/watchlists/1/items', {
      code: '000001', notes: '重点观察',
    });
  });
});

describe('removeFromWatchlist', () => {
  it('calls DELETE /watchlists/:id/items/:code', async () => {
    mockDelete.mockResolvedValueOnce({});
    await removeFromWatchlist(1, '000001');
    expect(mockDelete).toHaveBeenCalledWith('/watchlists/1/items/000001');
  });
});

describe('batchAddItems', () => {
  it('calls POST with codes array', async () => {
    mockPost.mockResolvedValueOnce({
      data: { id: 1, name: 'WL', stock_count: 2, items: [] },
    });
    await batchAddItems(1, ['000001', '600519']);
    expect(mockPost).toHaveBeenCalledWith('/watchlists/1/items/batch', {
      codes: ['000001', '600519'],
    });
  });
});

// ── Backtest ────────────────────────────────────────

describe('fetchBacktestResults', () => {
  it('calls GET /backtest/history', async () => {
    mockGet.mockResolvedValueOnce({ data: [] });
    const result = await fetchBacktestResults();
    expect(mockGet).toHaveBeenCalledWith('/backtest/history');
    expect(result).toEqual([]);
  });

  it('maps history items to results', async () => {
    mockGet.mockResolvedValueOnce({
      data: [{
        task_id: 'abc123', code: '000001', strategy: 'sma_cross',
        status: 'completed', total_return: 0.15, sharpe: 1.2,
        max_drawdown: -0.1, created_at: '2024-01-01',
      }],
    });
    const result = await fetchBacktestResults();
    expect(result[0]).toMatchObject({
      id: 'abc123',
      strategy_name: 'sma_cross',
      status: 'done',
      metrics: expect.objectContaining({ total_return: 0.15, sharpe: 1.2, max_drawdown: -0.1 }),
    });
  });

  it('calls /strategies/:id/results when strategyId is provided', async () => {
    mockGet.mockResolvedValueOnce({ data: [] });
    const result = await fetchBacktestResults(1);
    expect(mockGet).toHaveBeenCalledWith('/strategies/1/results');
    expect(result).toEqual([]);
  });

  it('maps strategy results preserving strategy_id', async () => {
    const strategyResult = {
      id: 'abc123',
      db_id: 42,
      strategy_id: 1,
      stock_codes: ['000001'],
      params: { period: 20 },
      start_date: '2024-01-01',
      end_date: '2024-06-30',
      metrics: { total_return: 0.15, sharpe: 1.2, max_drawdown: -0.1 },
      equity_curve: [{ date: '2024-01-02', value: 1.0 }, { date: '2024-01-03', value: 1.01 }],
      drawdown_curve: [{ date: '2024-01-02', value: 0 }, { date: '2024-01-03', value: -0.005 }],
      benchmark_curve: null,
      yearly_returns: [{ year: 2024, value: 0.15 }],
      monthly_returns: [{ year: 2024, month: 1, value: 0.02 }],
      trades: [{ date: '2024-01-10', action: 'buy', price: 10.5, quantity: 100, pnl: 0 }],
      status: 'completed',
      created_at: '2024-01-01T00:00:00',
    };
    mockGet.mockResolvedValueOnce({ data: [strategyResult] });
    const result = await fetchBacktestResults(1);
    expect(result).toHaveLength(1);
    const bt = result[0];
    expect(bt.id).toBe('abc123');
    expect(bt.strategy_id).toBe(1);
    expect(bt.stock_codes).toEqual(['000001']);
    expect(bt.params).toEqual({ period: 20 });
    expect(bt.start_date).toBe('2024-01-01');
    expect(bt.end_date).toBe('2024-06-30');
    expect(bt.metrics).toMatchObject({ total_return: 0.15, sharpe: 1.2, max_drawdown: -0.1 });
    expect(bt.equity_curve).toEqual([{ date: '2024-01-02', value: 1.0 }, { date: '2024-01-03', value: 1.01 }]);
    expect(bt.drawdown_curve).toEqual([{ date: '2024-01-02', value: 0 }, { date: '2024-01-03', value: -0.005 }]);
    expect(bt.yearly_returns).toEqual([{ year: 2024, value: 0.15 }]);
    expect(bt.monthly_returns).toEqual([{ year: 2024, month: 1, value: 0.02 }]);
    expect(bt.trades).toEqual([{ date: '2024-01-10', action: 'buy', price: 10.5, quantity: 100, pnl: 0 }]);
    expect(bt.status).toBe('done');
  });
});

describe('fetchBacktestResult', () => {
  it('calls GET /backtest/:id', async () => {
    mockGet.mockResolvedValueOnce({
      data: {
        task_id: 'abc123', status: 'completed', request: null,
        metrics: null, error: null, created_at: '', completed_at: null,
      },
    });
    const result = await fetchBacktestResult('abc123');
    expect(mockGet).toHaveBeenCalledWith('/backtest/abc123');
    expect(result).toBeDefined();
    expect(result!.id).toBe('abc123');
  });
});

describe('submitBacktest', () => {
  it('calls POST /backtest/run', async () => {
    mockPost.mockResolvedValueOnce({ data: { task_id: 'task1' } });
    const result = await submitBacktest({
      strategy_id: 1,
      code: '000001', strategy: 'sma_cross',
      start_date: '2024-01-01', end_date: '2024-12-31',
      initial_capital: 100000, params: { period: '20' },
    });
    expect(mockPost).toHaveBeenCalledWith('/backtest/run', expect.objectContaining({
      strategy_id: 1, code: '000001', strategy: 'sma_cross', commission: 0.0005, slippage: 0.001,
    }));
    expect(result).toEqual({ task_id: 'task1' });
  });
});

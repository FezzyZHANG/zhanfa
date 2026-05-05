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

import { renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { QuoteItem } from '@/types';

const mockNavigate = vi.fn();
let mockSearch: Record<string, string> = {};

vi.mock('@tanstack/react-router', () => ({
  useSearch: () => mockSearch,
  useNavigate: () => mockNavigate,
}));

import { useWatchlistUrlFilters } from './useWatchlistUrlFilters';

function item(overrides: Partial<QuoteItem>): QuoteItem {
  return {
    code: '000001',
    name: '平安银行',
    latest_price: 10,
    change_pct: 0.01,
    pe: 8,
    pb: 1,
    dividend_yield: 0.03,
    notes: null,
    data_status: null,
    data_freshness: 'unknown',
    ...overrides,
  };
}

describe('useWatchlistUrlFilters', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSearch = {};
  });

  it('applies search, PE and change filters together', () => {
    mockSearch = { search: '银行', peMin: '5', peMax: '10', changeDir: 'up' };
    const { result } = renderHook(() => useWatchlistUrlFilters());

    const filtered = result.current.applyFilters([
      item({ code: '000001', name: '平安银行', pe: 8, change_pct: 0.01 }),
      item({ code: '600519', name: '贵州茅台', pe: 20, change_pct: 0.02 }),
      item({ code: '000002', name: '银行B', pe: 7, change_pct: -0.01 }),
    ]);

    expect(filtered.map((i) => i.code)).toEqual(['000001']);
  });

  it('writes sort updates to URL search params', () => {
    const { result } = renderHook(() => useWatchlistUrlFilters());

    result.current.setSort('pe', 'desc');

    expect(mockNavigate).toHaveBeenCalledWith({
      search: { sortKey: 'pe', sortDir: 'desc' },
      replace: true,
    });
  });
});

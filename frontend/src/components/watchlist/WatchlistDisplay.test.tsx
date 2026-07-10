import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { QuoteItem } from '@/types';

const mockNavigate = vi.fn();
let applyFiltersMock = (items: QuoteItem[]) => items;

vi.mock('@tanstack/react-router', () => ({
  useNavigate: () => mockNavigate,
}));

vi.mock('@/hooks/useWatchlistUrlFilters', () => ({
  useWatchlistUrlFilters: () => ({
    sortKey: 'code',
    sortDir: 'asc',
    searchText: '',
    peMin: undefined,
    peMax: undefined,
    changeDir: '',
    setSort: vi.fn(),
    setSearchText: vi.fn(),
    setPeRange: vi.fn(),
    setChangeFilter: vi.fn(),
    applyFilters: applyFiltersMock,
  }),
}));

import { WatchlistCards } from './WatchlistCards';
import { WatchlistTable } from './WatchlistTable';

function quote(overrides: Partial<QuoteItem> = {}): QuoteItem {
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

describe('watchlist display components', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    applyFiltersMock = (items) => items;
  });

  it('renders filtered table rows and triggers batch remove', () => {
    const onBatchRemove = vi.fn();
    applyFiltersMock = (items) => items.filter((item) => item.pe != null && item.pe >= 10);

    render(
      <WatchlistTable
        quotes={[quote({ code: '000001', pe: 8 }), quote({ code: '600519', name: '贵州茅台', pe: 20 })]}
        onRemove={vi.fn()}
        onBatchRemove={onBatchRemove}
        onEditNotes={vi.fn()}
      />,
    );

    expect(screen.queryByText('000001')).toBeNull();
    expect(screen.getByText('600519')).toBeDefined();

    fireEvent.click(screen.getAllByRole('checkbox')[0]);
    fireEvent.click(screen.getByText('移除所选 (1)'));

    expect(onBatchRemove).toHaveBeenCalledWith(['600519']);
  });

  it('renders cards and delegates remove clicks', () => {
    const onRemove = vi.fn();

    render(<WatchlistCards quotes={[quote({ code: '600519', name: '贵州茅台' })]} onRemove={onRemove} />);
    fireEvent.click(screen.getByText('移除'));

    expect(onRemove).toHaveBeenCalledWith('600519');
    expect(mockNavigate).not.toHaveBeenCalled();
  });
});

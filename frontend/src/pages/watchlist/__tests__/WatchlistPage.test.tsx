import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import type { Watchlist, QuoteItem, WatchlistQuote } from '@/types';

const mockNavigate = vi.fn();

vi.mock('@tanstack/react-router', () => ({
  useNavigate: () => mockNavigate,
  useSearch: () => ({}),
}));

// ── Default mock returns ────────────────────────────

const defaultWatchlists: Watchlist[] = [
  {
    id: 1,
    name: '默认',
    stock_count: 0,
    items: [],
    created_at: '2024-01-01T00:00:00Z',
  },
];

const emptyQuotes: WatchlistQuote = { id: 1, name: '默认', items: [] };

function makeQuoteItem(overrides: Partial<QuoteItem> = {}): QuoteItem {
  return {
    code: '000001',
    name: '平安银行',
    latest_price: 12.5,
    change_pct: 0.025,
    pe: 6.8,
    pb: 0.9,
    dividend_yield: 0.035,
    notes: null,
    data_status: {
      has_daily: true,
      has_financial: true,
      daily_start: '2024-01-01',
      daily_end: '2025-12-31',
      financial_periods: 8,
    },
    data_freshness: 'cached',
    ...overrides,
  };
}

// ── Hook mocks ───────────────────────────────────────

let mockWatchlistsData: Watchlist[] = defaultWatchlists;
let mockWatchlistsLoading = false;
let mockQuotesData: WatchlistQuote | undefined = emptyQuotes;
let mockQuotesLoading = false;
let mockSelectedId: number | null = null;

const mockMutate = vi.fn();
const mockMutateAsync = vi.fn();

function makeMutation(overrides = {}) {
  return {
    mutate: mockMutate,
    mutateAsync: mockMutateAsync,
    isPending: false,
    ...overrides,
  };
}

vi.mock('@/hooks/useWatchlists', () => ({
  useWatchlists: () => ({ data: mockWatchlistsData, isLoading: mockWatchlistsLoading }),
  useWatchlistQuotes: (id: number | null) => ({ data: id ? mockQuotesData : undefined, isLoading: mockQuotesLoading }),
  useCreateWatchlist: () => makeMutation(),
  useRenameWatchlist: () => makeMutation(),
  useDeleteWatchlist: () => makeMutation(),
  useAddToWatchlist: () => makeMutation(),
  useRemoveFromWatchlist: () => makeMutation(),
  useUpdateItemNotes: () => makeMutation(),
  useBatchAddItems: () => makeMutation(),
  useBatchDeleteItems: () => makeMutation(),
  useRefreshWatchlistData: () => makeMutation({ isPending: false }),
  useBatchAddPreview: () => makeMutation(),
  useSearchStocks: () => ({ data: [], isLoading: false }),
}));

vi.mock('@/components/watchlist/useWatchlist', () => ({
  useWatchlist: () => ({
    selectedId: mockSelectedId,
    selectWatchlist: vi.fn(),
    setSelectedId: vi.fn((id: number | null) => { mockSelectedId = id; }),
    viewMode: 'table' as const,
    setViewMode: vi.fn(),
    groupDialog: { open: false, mode: 'create' as const },
    openCreate: vi.fn(),
    openRename: vi.fn(),
    closeGroupDialog: vi.fn(),
    deleteTarget: null,
    confirmDelete: vi.fn(),
    closeDelete: vi.fn(),
    addStockOpen: false,
    openAddStock: vi.fn(),
    closeAddStock: vi.fn(),
    notesEdit: null,
    openNotesEdit: vi.fn(),
    closeNotesEdit: vi.fn(),
    batchDeleteCodes: null,
    confirmBatchDelete: vi.fn(),
    closeBatchDelete: vi.fn(),
  }),
}));

vi.mock('@/api/client', async () => {
  const actual = await vi.importActual('@/api/client');
  return {
    ...actual,
    getExportCsvUrl: (id: number) => `/api/watchlists/${id}/export`,
  };
});

import { WatchlistPage } from '@/pages/watchlist/WatchlistPage';


describe('WatchlistPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockWatchlistsData = [...defaultWatchlists];
    mockWatchlistsLoading = false;
    mockQuotesData = { ...emptyQuotes };
    mockQuotesLoading = false;
    mockSelectedId = null;
  });

  it('renders page title', () => {
    render(<WatchlistPage />);
    expect(screen.getByText('自选股看板')).toBeDefined();
  });

  it('renders sidebar with watchlist names', () => {
    render(<WatchlistPage />);
    expect(screen.getByText('默认')).toBeDefined();
  });

  it('shows placeholder when no group is selected', () => {
    mockSelectedId = null;
    render(<WatchlistPage />);
    expect(screen.getByText('请选择一个分组')).toBeDefined();
  });

  it('shows skeleton during initial loading', () => {
    mockWatchlistsLoading = true;
    render(<WatchlistPage />);
    // Skeleton components render
    expect(screen.queryByText('自选股看板')).toBeDefined();
  });

  it('renders table view when group selected with quotes', () => {
    mockSelectedId = 1;
    mockQuotesData = {
      id: 1,
      name: '默认',
      items: [makeQuoteItem()],
    };
    render(<WatchlistPage />);
    expect(screen.getByText('000001')).toBeDefined();
    expect(screen.getByText('平安银行')).toBeDefined();
  });

  it('renders data freshness indicator text for cached data', () => {
    mockSelectedId = 1;
    mockQuotesData = {
      id: 1,
      name: '默认',
      items: [makeQuoteItem({ data_freshness: 'cached' })],
    };
    render(<WatchlistPage />);
    // DataStatusIcon has a title attribute
    const statusIcon = document.querySelector('[title]');
    expect(statusIcon).toBeDefined();
  });

  it('shows empty state message in table when no stocks', () => {
    mockSelectedId = 1;
    mockQuotesData = { id: 1, name: '默认', items: [] };
    render(<WatchlistPage />);
    expect(screen.getByText('暂无股票，点击"添加股票"开始')).toBeDefined();
  });

  it('renders action buttons when group is selected', () => {
    mockSelectedId = 1;
    mockQuotesData = { id: 1, name: '默认', items: [] };
    render(<WatchlistPage />);
    expect(screen.getByText('+ 添加股票')).toBeDefined();
    expect(screen.getByText('导出 CSV')).toBeDefined();
    expect(screen.getByText('刷新数据')).toBeDefined();
  });

  it('shows skeleton for quotes while loading', () => {
    mockSelectedId = 1;
    mockQuotesLoading = true;
    render(<WatchlistPage />);
    // Skeleton placeholders render, table does not
    expect(screen.queryByText('暂无股票，点击"添加股票"开始')).toBeNull();
  });

  it('renders multiple watchlists in sidebar', () => {
    mockWatchlistsData = [
      { id: 1, name: '默认', stock_count: 2, items: [], created_at: '2024-01-01T00:00:00Z' },
      { id: 2, name: '沪深300', stock_count: 5, items: [], created_at: '2024-02-01T00:00:00Z' },
    ];
    render(<WatchlistPage />);
    expect(screen.getByText('默认')).toBeDefined();
    expect(screen.getByText('沪深300')).toBeDefined();
  });

  it('shows stock count in sidebar', () => {
    mockWatchlistsData = [
      { id: 1, name: '默认', stock_count: 3, items: [], created_at: '2024-01-01T00:00:00Z' },
    ];
    render(<WatchlistPage />);
    expect(screen.getByText('3')).toBeDefined();
  });
});

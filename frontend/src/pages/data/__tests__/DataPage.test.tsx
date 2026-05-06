import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DataPage } from '@/pages/DataPage';

const mockRefetch = vi.fn();
const mockInitMutate = vi.fn();
const mockRefreshMutateAsync = vi.fn();

let mockStats: unknown;
let mockStatsLoading: boolean;
let mockInitMutation: { mutate: ReturnType<typeof vi.fn>; isPending: boolean; data?: unknown; isError?: boolean; error?: Error };
let mockRefreshMutation: { mutateAsync: ReturnType<typeof vi.fn>; isPending: boolean };

vi.mock('@/hooks/useData', () => ({
  useDataStats: () => ({ data: mockStats, isLoading: mockStatsLoading, refetch: mockRefetch }),
  useRefreshData: () => mockRefreshMutation,
  useInitializeData: () => mockInitMutation,
}));

vi.mock('@/api/client', () => ({
  fetchStockDataStatus: vi.fn().mockResolvedValue(null),
}));

vi.mock('@/components/data/StockDataTable', () => ({
  StockDataTable: ({ data, loading }: { data: unknown[]; loading: boolean }) => (
    <div data-testid="stock-data-table">
      {loading ? 'table-loading' : `table-rows:${data.length}`}
    </div>
  ),
}));

vi.mock('@/components/data/DataStatsCards', () => ({
  DataStatsCards: () => <div data-testid="data-stats-cards" />,
}));

vi.mock('@/components/data/DataCoverageChart', () => ({
  DataCoverageChart: () => <div data-testid="data-coverage-chart" />,
}));

vi.mock('@/components/data/RefreshButton', () => ({
  RefreshButton: ({ onRefresh }: { onRefresh: (force: boolean) => void }) => (
    <button onClick={() => onRefresh(false)} data-testid="refresh-button">Refresh</button>
  ),
}));

vi.mock('@/components/ui/Button', () => ({
  Button: ({ children, onClick, disabled, variant, size }: Record<string, unknown>) => (
    <button onClick={onClick as () => void} disabled={disabled as boolean} data-testid="button">
      {children as string}
    </button>
  ),
}));

const emptyStats = {
  cache: {
    stock_count: 0, total_rows: 0, storage_bytes: 0,
    date_range_start: null, date_range_end: null,
    freq_stats: {}, last_refreshed_at: null,
  },
  database: {
    stock_count: 0, financial_count: 0, watchlist_count: 0,
    strategy_count: 0, backtest_count: 0,
  },
};

const populatedStats = {
  cache: {
    stock_count: 5000, total_rows: 5000000, storage_bytes: 1024000,
    date_range_start: '2020-01-01', date_range_end: '2025-12-31',
    freq_stats: { daily: 5000 }, last_refreshed_at: '2025-01-01T15:30:00',
  },
  database: {
    stock_count: 5000, financial_count: 4800, watchlist_count: 3,
    strategy_count: 8, backtest_count: 42,
  },
};

function setupMocks() {
  vi.clearAllMocks();
  mockStats = undefined;
  mockStatsLoading = false;
  mockInitMutation = { mutate: mockInitMutate, isPending: false };
  mockRefreshMutation = { mutateAsync: mockRefreshMutateAsync, isPending: false };
}

beforeEach(setupMocks);

describe('DataPage', () => {
  it('shows loading skeleton when stats are loading', () => {
    mockStatsLoading = true;
    mockStats = undefined;
    render(<DataPage />);
    // Should show skeleton pulsing cards
    expect(screen.getByText('数据管理')).toBeDefined();
    const skeletons = document.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('shows uninitialized state when stock counts are zero', () => {
    mockStats = emptyStats;
    mockStatsLoading = false;
    render(<DataPage />);
    expect(screen.getByText('尚未初始化数据')).toBeDefined();
    expect(screen.getByText('开始初始化数据')).toBeDefined();
  });

  it('shows initialized state when stats are populated', () => {
    mockStats = populatedStats;
    mockStatsLoading = false;
    render(<DataPage />);
    expect(screen.getByTestId('data-stats-cards')).toBeDefined();
    expect(screen.getByTestId('data-coverage-chart')).toBeDefined();
    expect(screen.getByTestId('stock-data-table')).toBeDefined();
  });

  it('shows init success message', () => {
    mockStats = emptyStats;
    mockInitMutation = {
      mutate: mockInitMutate,
      isPending: false,
      data: { message: '已导入 5000 只股票到 stocks 表' },
    };
    render(<DataPage />);
    expect(screen.getByText('已导入 5000 只股票到 stocks 表')).toBeDefined();
  });

  it('shows init error message', () => {
    mockStats = emptyStats;
    mockInitMutation = {
      mutate: mockInitMutate,
      isPending: false,
      isError: true,
      error: new Error('Network Error'),
    };
    render(<DataPage />);
    expect(screen.getByText('Network Error')).toBeDefined();
  });

  it('shows generic error for non-Error init failures', () => {
    mockStats = emptyStats;
    mockInitMutation = {
      mutate: mockInitMutate,
      isPending: false,
      isError: true,
    };
    render(<DataPage />);
    expect(screen.getByText('初始化失败')).toBeDefined();
  });

  it('disables init button while pending', () => {
    mockStats = emptyStats;
    mockInitMutation = { mutate: mockInitMutate, isPending: true };
    render(<DataPage />);
    const buttons = screen.getAllByTestId('button');
    const initButtons = buttons.filter(
      (b) => b.textContent?.includes('初始化中')
    );
    expect(initButtons.length).toBeGreaterThan(0);
  });

  it('hides uninitialized state when stock_count > 0', () => {
    mockStats = {
      cache: { ...emptyStats.cache, stock_count: 1 },
      database: emptyStats.database,
    };
    render(<DataPage />);
    expect(screen.queryByText('尚未初始化数据')).toBeNull();
    expect(screen.getByTestId('data-stats-cards')).toBeDefined();
  });
});

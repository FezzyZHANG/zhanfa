import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import type { Strategy, BacktestResult } from '@/types';

const mockNavigate = vi.fn();

vi.mock('@tanstack/react-router', () => ({
  useParams: () => ({ strategyId: '1' }),
  useNavigate: () => mockNavigate,
}));

const mockUseStrategy = vi.fn();
const mockUseBacktestResults = vi.fn();

vi.mock('@/hooks/useStrategies', () => ({
  useStrategy: (id: number) => mockUseStrategy(id),
}));

vi.mock('@/hooks/useBacktests', () => ({
  useBacktestResults: (id?: number) => mockUseBacktestResults(id),
}));

// react-markdown uses ESM; mock it
vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => children,
}));

vi.mock('remark-gfm', () => ({ default: {} }));

import { StrategyDetailPage } from '@/pages/strategies/StrategyDetailPage';

function makeStrategy(overrides: Partial<Strategy> = {}): Strategy {
  return {
    id: 1,
    name: '双均线交叉',
    category: 'trend',
    description: '基于短期和长期均线交叉产生交易信号',
    params: {
      fast_period: { type: 'int', default: 5, description: '快线周期' },
      slow_period: { type: 'int', default: 20, description: '慢线周期' },
    },
    code_ref: 'sma_cross',
    backtest_count: 3,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-06-15T00:00:00Z',
    ...overrides,
  };
}

function makeBacktestResult(overrides: Partial<BacktestResult> = {}): BacktestResult {
  return {
    id: '1',
    strategy_id: 1,
    strategy_name: '双均线交叉',
    stock_codes: ['000001'],
    params: { fast_period: 5, slow_period: 20 },
    start_date: '2024-01-01',
    end_date: '2024-12-31',
    metrics: {
      total_return: 0.15,
      ann_return: 0.14,
      ann_volatility: 0.2,
      sharpe: 1.2,
      sortino: 1.5,
      max_drawdown: -0.1,
      calmar: 1.4,
      win_rate: 0.55,
      years: 1,
    },
    equity_curve: [],
    drawdown_curve: [],
    yearly_returns: [],
    monthly_returns: [],
    trades: [],
    status: 'done',
    created_at: '2024-01-01T00:00:00Z',
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  mockUseStrategy.mockReturnValue({ data: makeStrategy(), isLoading: false });
  mockUseBacktestResults.mockReturnValue({ data: [makeBacktestResult()] });
});

describe('StrategyDetailPage', () => {
  it('renders strategy name and category', () => {
    render(<StrategyDetailPage />);
    expect(screen.getByText('双均线交叉')).toBeDefined();
    expect(screen.getByText('趋势跟踪')).toBeDefined();
  });

  it('renders strategy description', () => {
    render(<StrategyDetailPage />);
    expect(screen.getByText(/基于短期和长期均线交叉/)).toBeDefined();
  });

  it('renders code reference when present', () => {
    render(<StrategyDetailPage />);
    expect(screen.getByText('sma_cross')).toBeDefined();
  });

  it('does not render code ref when absent', () => {
    mockUseStrategy.mockReturnValue({
      data: makeStrategy({ code_ref: null }),
      isLoading: false,
    });
    render(<StrategyDetailPage />);
    expect(screen.queryByText('sma_cross')).toBeNull();
  });

  it('renders backtest count', () => {
    render(<StrategyDetailPage />);
    expect(screen.getByText('3')).toBeDefined();
  });

  it('renders backtest records with dates', () => {
    render(<StrategyDetailPage />);
    expect(screen.getByText('2024-01-01 ~ 2024-12-31')).toBeDefined();
  });

  it('renders backtest metric values', () => {
    render(<StrategyDetailPage />);
    expect(screen.getByText('15.00%')).toBeDefined(); // total_return
    expect(screen.getByText('1.20')).toBeDefined(); // sharpe
    expect(screen.getByText('-10.00%')).toBeDefined(); // max_drawdown
  });

  it('shows loading skeleton when loading', () => {
    mockUseStrategy.mockReturnValue({ data: null, isLoading: true });
    const { container } = render(<StrategyDetailPage />);
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('shows "策略不存在" when strategy is null', () => {
    mockUseStrategy.mockReturnValue({ data: null, isLoading: false });
    render(<StrategyDetailPage />);
    expect(screen.getByText('策略不存在')).toBeDefined();
  });

  it('shows "暂无回测记录" when backtests empty', () => {
    mockUseBacktestResults.mockReturnValue({ data: [] });
    render(<StrategyDetailPage />);
    expect(screen.getByText('暂无回测记录')).toBeDefined();
  });

  it('shows "暂无回测记录" when backtests null', () => {
    mockUseBacktestResults.mockReturnValue({ data: null });
    render(<StrategyDetailPage />);
    expect(screen.getByText('暂无回测记录')).toBeDefined();
  });

  it('handles backtest with missing metrics gracefully', () => {
    const bt = makeBacktestResult({
      metrics: {
        total_return: 0,
        ann_return: 0,
        ann_volatility: 0,
        sharpe: undefined as unknown as number,
        sortino: undefined as unknown as number,
        max_drawdown: undefined as unknown as number,
        calmar: undefined as unknown as number,
        win_rate: undefined as unknown as number,
        years: 0,
      },
    });
    mockUseBacktestResults.mockReturnValue({ data: [bt] });
    // Should not throw
    expect(() => render(<StrategyDetailPage />)).not.toThrow();
    // Should show '--' for missing values
    const dashes = screen.getAllByText('--');
    expect(dashes.length).toBeGreaterThanOrEqual(2);
  });

  it('renders param chips for strategy params', () => {
    render(<StrategyDetailPage />);
    // StrategyParams renders a table: param name and default in separate cells
    expect(screen.getByText('fast_period')).toBeDefined();
    expect(screen.getByText('slow_period')).toBeDefined();
    expect(screen.getByText('5')).toBeDefined();
    expect(screen.getByText('20')).toBeDefined();
  });
});

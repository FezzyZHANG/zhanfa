import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import type { Strategy, BacktestResult, StockInfo } from '@/types';

const mockNavigate = vi.fn();

vi.mock('@tanstack/react-router', () => ({
  useNavigate: () => mockNavigate,
}));

const mockUseStrategies = vi.fn();
const mockUseBacktestResults = vi.fn();
const mockUseStocks = vi.fn();
const mockUseBacktestSubmit = vi.fn();
const mockUseBacktestTask = vi.fn();

vi.mock('@/hooks/useStrategies', () => ({
  useStrategies: () => mockUseStrategies(),
}));

vi.mock('@/hooks/useBacktests', () => ({
  useBacktestResults: () => mockUseBacktestResults(),
}));

vi.mock('@/hooks/useStocks', () => ({
  useStocks: () => mockUseStocks(),
}));

vi.mock('@/hooks/useBacktest', () => ({
  useBacktestSubmit: () => mockUseBacktestSubmit(),
  useBacktestTask: (id?: string) => mockUseBacktestTask(id),
}));

import { BacktestPage } from '@/pages/backtest/BacktestPage';

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
    params: {},
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

function makeStock(): StockInfo {
  return {
    code: '000001',
    name: '平安银行',
    exchange: 'SZ',
    industry: '银行',
    market_cap: 300_000_000_000,
    listed_date: '1991-04-03',
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  mockUseStrategies.mockReturnValue({ data: [makeStrategy()] });
  mockUseBacktestResults.mockReturnValue({
    data: [makeBacktestResult()],
    isLoading: false,
  });
  mockUseStocks.mockReturnValue({ data: [makeStock()] });
  mockUseBacktestSubmit.mockReturnValue({
    submit: vi.fn(),
    taskId: null,
    isSubmitting: false,
  });
  mockUseBacktestTask.mockReturnValue(null);
});

describe('BacktestPage', () => {
  it('renders page title', () => {
    render(<BacktestPage />);
    expect(screen.getByText('回测')).toBeDefined();
  });

  it('renders backtest history list', () => {
    render(<BacktestPage />);
    expect(screen.getByText('历史回测')).toBeDefined();
    // "双均线交叉" appears both in form dropdown and card — use getAllByText
    const matches = screen.getAllByText('双均线交叉');
    expect(matches.length).toBeGreaterThanOrEqual(2);
  });

  it('renders backtest metric values', () => {
    render(<BacktestPage />);
    expect(screen.getByText('15.00%')).toBeDefined();
    expect(screen.getByText('1.20')).toBeDefined();
    expect(screen.getByText('-10.00%')).toBeDefined();
  });

  it('renders status badge for done backtest', () => {
    render(<BacktestPage />);
    expect(screen.getByText('已完成')).toBeDefined();
  });

  it('renders status badge for pending backtest', () => {
    mockUseBacktestResults.mockReturnValue({
      data: [makeBacktestResult({ status: 'pending', metrics: null as unknown as BacktestResult['metrics'] })],
      isLoading: false,
    });
    render(<BacktestPage />);
    expect(screen.getByText('等待中')).toBeDefined();
  });

  it('renders status badge for failed backtest', () => {
    mockUseBacktestResults.mockReturnValue({
      data: [makeBacktestResult({ status: 'failed', metrics: null as unknown as BacktestResult['metrics'] })],
      isLoading: false,
    });
    render(<BacktestPage />);
    expect(screen.getByText('失败')).toBeDefined();
  });

  it('does not render metrics for non-done backtests', () => {
    mockUseBacktestResults.mockReturnValue({
      data: [makeBacktestResult({ status: 'running', metrics: null as unknown as BacktestResult['metrics'] })],
      isLoading: false,
    });
    render(<BacktestPage />);
    expect(screen.getByText('运行中')).toBeDefined();
    expect(screen.queryByText('总收益')).toBeNull();
  });

  it('shows empty state when no backtests', () => {
    mockUseBacktestResults.mockReturnValue({ data: [], isLoading: false });
    render(<BacktestPage />);
    expect(screen.getByText('暂无回测记录，填写左侧表单开始回测')).toBeDefined();
  });

  it('shows loading skeleton when loading', () => {
    mockUseBacktestResults.mockReturnValue({ data: null, isLoading: true });
    const { container } = render(<BacktestPage />);
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('navigates to detail on card click', () => {
    render(<BacktestPage />);
    // Strategy name appears both in form dropdown and in history card
    // Use getAllByText and click the one inside a card (not in option)
    const elements = screen.getAllByText('双均线交叉');
    const cardTitle = elements.find((el) => el.tagName === 'H3');
    expect(cardTitle).toBeDefined();
    const card = cardTitle!.closest('.cursor-pointer');
    if (card) fireEvent.click(card);
    expect(mockNavigate).toHaveBeenCalledWith(
      expect.objectContaining({ to: '/backtest/$backtestId' })
    );
  });

  it('handles backtest with missing sharpe gracefully', () => {
    const bt = makeBacktestResult({
      metrics: {
        ...makeBacktestResult().metrics,
        sharpe: undefined as unknown as number,
      },
    });
    mockUseBacktestResults.mockReturnValue({ data: [bt], isLoading: false });
    // Should not throw — even though .toFixed(2) on undefined would crash
    expect(() => render(<BacktestPage />)).not.toThrow();
  });
});

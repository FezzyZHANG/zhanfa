import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import type { BacktestResult } from '@/types';

// lightweight-charts and echarts crash in jsdom — mock them
vi.mock('lightweight-charts', () => ({
  LineSeries: 'LineSeries',
  AreaSeries: 'AreaSeries',
  HistogramSeries: 'HistogramSeries',
  CandlestickSeries: 'CandlestickSeries',
  createSeriesMarkers: vi.fn(),
  createChart: () => ({
    addSeries: vi.fn(() => ({
      setData: vi.fn(),
      priceScale: () => ({
        applyOptions: vi.fn(),
      }),
    })),
    removeSeries: vi.fn(),
    remove: vi.fn(),
    resize: vi.fn(),
    timeScale: () => ({
      fitContent: vi.fn(),
      setVisibleLogicalRange: vi.fn(),
    }),
    subscribeCrosshairMove: vi.fn(),
    unsubscribeCrosshairMove: vi.fn(),
    applyOptions: vi.fn(),
  }),
}));

vi.mock('echarts-for-react', () => ({
  default: () => null,
}));

vi.mock('echarts', () => ({
  init: () => null,
  getInstanceByDom: () => null,
}));

vi.mock('@tanstack/react-router', () => ({
  useParams: () => ({ backtestId: 'abc123' }),
}));

const mockUseBacktestResult = vi.fn();

vi.mock('@/hooks/useBacktests', () => ({
  useBacktestResult: (id: string) => mockUseBacktestResult(id),
}));

import { BacktestDetailPage } from '@/pages/backtest/BacktestDetailPage';

function makeBacktestResult(overrides: Partial<BacktestResult> = {}): BacktestResult {
  return {
    id: 'abc123',
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
    equity_curve: [
      { date: '2024-01-01', value: 1.0 },
      { date: '2024-12-31', value: 1.15 },
    ],
    drawdown_curve: [
      { date: '2024-01-01', value: 0 },
      { date: '2024-06-15', value: -0.05 },
      { date: '2024-12-31', value: -0.02 },
    ],
    yearly_returns: [{ year: 2024, value: 0.15 }],
    monthly_returns: Array.from({ length: 12 }, (_, i) => ({
      year: 2024,
      month: i + 1,
      value: 0.01 + Math.random() * 0.02,
    })),
    trades: [
      { date: '2024-03-15', action: 'buy', price: 10.5, quantity: 1000 },
      { date: '2024-06-20', action: 'sell', price: 12.0, quantity: 1000, pnl: 1500 },
    ],
    status: 'done',
    created_at: '2024-01-01T00:00:00Z',
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  mockUseBacktestResult.mockReturnValue({
    data: makeBacktestResult(),
    isLoading: false,
  });
});

describe('BacktestDetailPage', () => {
  it('renders backtest result header', () => {
    render(<BacktestDetailPage />);
    expect(screen.getByText('回测结果')).toBeDefined();
  });

  it('renders strategy name and date range', () => {
    render(<BacktestDetailPage />);
    expect(screen.getByText(/双均线交叉/)).toBeDefined();
    expect(screen.getByText(/2024-01-01/)).toBeDefined();
  });

  it('renders metric cards via BacktestMetrics', () => {
    render(<BacktestDetailPage />);
    expect(screen.getByText('总收益率')).toBeDefined();
    expect(screen.getByText('夏普比率')).toBeDefined();
  });

  it('shows loading skeleton while loading', () => {
    mockUseBacktestResult.mockReturnValue({ data: null, isLoading: true });
    const { container } = render(<BacktestDetailPage />);
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('shows "回测结果不存在" when result is null', () => {
    mockUseBacktestResult.mockReturnValue({ data: null, isLoading: false });
    render(<BacktestDetailPage />);
    expect(screen.getByText('回测结果不存在')).toBeDefined();
  });

  it('shows pending state', () => {
    mockUseBacktestResult.mockReturnValue({
      data: makeBacktestResult({ status: 'pending' }),
      isLoading: false,
    });
    render(<BacktestDetailPage />);
    expect(screen.getByText('等待回测开始...')).toBeDefined();
  });

  it('shows running state', () => {
    mockUseBacktestResult.mockReturnValue({
      data: makeBacktestResult({ status: 'running' }),
      isLoading: false,
    });
    render(<BacktestDetailPage />);
    expect(screen.getByText('回测运行中...')).toBeDefined();
  });

  it('shows failed state', () => {
    mockUseBacktestResult.mockReturnValue({
      data: makeBacktestResult({ status: 'failed' }),
      isLoading: false,
    });
    render(<BacktestDetailPage />);
    expect(screen.getByText('回测失败，请重试')).toBeDefined();
  });

  it('renders with null strategy_name using fallback', () => {
    mockUseBacktestResult.mockReturnValue({
      data: makeBacktestResult({ strategy_name: undefined }),
      isLoading: false,
    });
    render(<BacktestDetailPage />);
    expect(screen.getByText(/策略 #1/)).toBeDefined();
  });

  it('handles empty equity/drawdown curves', () => {
    mockUseBacktestResult.mockReturnValue({
      data: makeBacktestResult({
        equity_curve: [],
        drawdown_curve: [],
        yearly_returns: [],
        monthly_returns: [],
        trades: [],
      }),
      isLoading: false,
    });
    expect(() => render(<BacktestDetailPage />)).not.toThrow();
  });

  it('handles partial metrics without crash', () => {
    mockUseBacktestResult.mockReturnValue({
      data: makeBacktestResult({
        metrics: {
          total_return: 0,
          ann_return: 0,
          ann_volatility: 0,
          max_drawdown: 0,
          win_rate: 0,
          years: 0,
          sharpe: undefined as unknown as number,
          sortino: undefined as unknown as number,
          calmar: undefined as unknown as number,
        },
      }),
      isLoading: false,
    });
    expect(() => render(<BacktestDetailPage />)).not.toThrow();
  });
});

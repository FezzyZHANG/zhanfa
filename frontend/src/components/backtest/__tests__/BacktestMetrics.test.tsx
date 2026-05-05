import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BacktestMetrics } from '@/components/backtest/BacktestMetrics';
import type { BacktestMetrics as BM } from '@/types';

function makeMetrics(overrides: Partial<BM> = {}): BM {
  return {
    total_return: 0.15,
    ann_return: 0.14,
    ann_volatility: 0.2,
    sharpe: 1.2,
    sortino: 1.5,
    max_drawdown: -0.1,
    calmar: 1.4,
    win_rate: 0.55,
    years: 1,
    ...overrides,
  };
}

describe('BacktestMetrics', () => {
  it('renders all 8 metric cards', () => {
    const { container } = render(<BacktestMetrics metrics={makeMetrics()} />);
    const cards = container.querySelectorAll('.rounded-xl');
    expect(cards.length).toBe(8);
  });

  it('renders total return as percentage', () => {
    render(<BacktestMetrics metrics={makeMetrics()} />);
    expect(screen.getByText('总收益率')).toBeDefined();
    expect(screen.getByText('15.00%')).toBeDefined();
  });

  it('renders sharpe as number', () => {
    render(<BacktestMetrics metrics={makeMetrics()} />);
    expect(screen.getByText('夏普比率')).toBeDefined();
    expect(screen.getByText('1.20')).toBeDefined();
  });

  it('renders max drawdown with red color', () => {
    render(<BacktestMetrics metrics={makeMetrics({ max_drawdown: -0.3 })} />);
    expect(screen.getByText('最大回撤')).toBeDefined();
    expect(screen.getByText('-30.00%')).toBeDefined();
  });

  it('skips undefined metric values', () => {
    const metrics = makeMetrics({
      sharpe: undefined as unknown as number,
      sortino: undefined as unknown as number,
    });
    const { container } = render(<BacktestMetrics metrics={metrics} />);
    const cards = container.querySelectorAll('.rounded-xl');
    expect(cards.length).toBe(6); // 8 - 2 = 6
  });

  it('skips null metric values', () => {
    const metrics = makeMetrics({
      sharpe: null as unknown as number,
    });
    const { container } = render(<BacktestMetrics metrics={metrics} />);
    const cards = container.querySelectorAll('.rounded-xl');
    expect(cards.length).toBe(7); // 8 - 1 = 7
  });

  it('handles all undefined metrics without crash', () => {
    const empty = {} as BM;
    expect(() => render(<BacktestMetrics metrics={empty} />)).not.toThrow();
    const { container } = render(<BacktestMetrics metrics={empty} />);
    expect(container.querySelectorAll('.rounded-xl').length).toBe(0);
  });

  it('shows green for positive return', () => {
    const { container } = render(<BacktestMetrics metrics={makeMetrics({ total_return: 0.2 })} />);
    const greenEls = container.querySelectorAll('.text-green-600');
    expect(greenEls.length).toBeGreaterThan(0);
  });

  it('shows red for negative return', () => {
    const { container } = render(<BacktestMetrics metrics={makeMetrics({ total_return: -0.1 })} />);
    const redEls = container.querySelectorAll('.text-red-500');
    expect(redEls.length).toBeGreaterThan(0);
  });

  it('shows yellow for moderate drawdown', () => {
    const { container } = render(<BacktestMetrics metrics={makeMetrics({ max_drawdown: -0.15 })} />);
    const yellowEls = container.querySelectorAll('.text-yellow-600');
    expect(yellowEls.length).toBeGreaterThan(0);
  });

  it('shows green for win_rate >= 0.5', () => {
    const { container } = render(<BacktestMetrics metrics={makeMetrics({ win_rate: 0.6 })} />);
    const greenEls = container.querySelectorAll('.text-green-600');
    expect(greenEls.length).toBeGreaterThan(0);
  });
});

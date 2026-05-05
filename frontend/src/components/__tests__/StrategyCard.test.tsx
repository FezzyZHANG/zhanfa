import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { StrategyCard } from '@/components/strategy/StrategyCard';
import type { Strategy } from '@/types';

function makeStrategy(overrides: Partial<Strategy> = {}): Strategy {
  return {
    id: 1,
    name: '双均线交叉策略',
    category: 'trend',
    description: '基于短期和长期均线交叉产生交易信号',
    params: {
      fast_period: { type: 'int', default: 5, description: '快线周期' },
      slow_period: { type: 'int', default: 20, description: '慢线周期' },
    },
    created_at: '2024-01-01',
    updated_at: '2024-01-01',
    ...overrides,
  };
}

describe('StrategyCard', () => {
  it('renders strategy name', () => {
    render(<StrategyCard strategy={makeStrategy()} />);
    expect(screen.getByText('双均线交叉策略')).toBeDefined();
  });

  it('renders strategy description', () => {
    render(<StrategyCard strategy={makeStrategy()} />);
    expect(screen.getByText(/基于短期和长期均线交叉/)).toBeDefined();
  });

  it('renders category badge', () => {
    render(<StrategyCard strategy={makeStrategy()} />);
    expect(screen.getByText('趋势跟踪')).toBeDefined();
  });

  it('renders param chips', () => {
    render(<StrategyCard strategy={makeStrategy()} />);
    expect(screen.getByText('fast_period=5')).toBeDefined();
    expect(screen.getByText('slow_period=20')).toBeDefined();
  });

  it('shows "+N more" when params exceed 3', () => {
    const strategy = makeStrategy({
      params: {
        a: { type: 'int', default: 1, description: '' },
        b: { type: 'int', default: 2, description: '' },
        c: { type: 'int', default: 3, description: '' },
        d: { type: 'int', default: 4, description: '' },
      },
    });
    render(<StrategyCard strategy={strategy} />);
    expect(screen.getByText('+1 更多')).toBeDefined();
  });

  it('calls onClick when clicked', () => {
    const onClick = vi.fn();
    const { container } = render(<StrategyCard strategy={makeStrategy()} onClick={onClick} />);
    const card = container.firstChild as HTMLElement;
    fireEvent.click(card);
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('renders momentum category label', () => {
    render(<StrategyCard strategy={makeStrategy({ category: 'momentum' })} />);
    expect(screen.getByText('动量')).toBeDefined();
  });

  it('renders fundamental category label', () => {
    render(<StrategyCard strategy={makeStrategy({ category: 'fundamental' })} />);
    expect(screen.getByText('基本面')).toBeDefined();
  });

  it('renders composite category label', () => {
    render(<StrategyCard strategy={makeStrategy({ category: 'composite' })} />);
    expect(screen.getByText('复合策略')).toBeDefined();
  });
});

import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { Strategy } from '@/types';

const { mockSubmitBacktest } = vi.hoisted(() => ({
  mockSubmitBacktest: vi.fn(),
}));

vi.mock('@/api/client', () => ({
  submitBacktest: mockSubmitBacktest,
  getBacktestTask: vi.fn(),
}));

import { useBacktestSubmit } from './useBacktest';

const strategies: Strategy[] = [
  {
    id: 1,
    name: '双均线',
    category: 'trend',
    description: '',
    params: {},
    code_ref: 'zhanfa.strategies.trend.sma_cross.SMACross',
    created_at: '',
    updated_at: '',
  },
];

describe('useBacktestSubmit', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSubmitBacktest.mockResolvedValue({ task_id: 'task-1' });
  });

  it('passes normalized submit params to the API client', async () => {
    const { result } = renderHook(() => useBacktestSubmit(strategies));

    await act(async () => {
      await result.current.submit({
        strategy_id: 1,
        stock_code: '000001',
        start_date: '2024-01-01',
        end_date: '2024-12-31',
        initial_capital: 100000,
        params: { fast: '5', slow: '20' },
      });
    });

    expect(mockSubmitBacktest).toHaveBeenCalledWith({
      strategy_id: 1,
      code: '000001',
      strategy: 'zhanfa.strategies.trend.sma_cross.SMACross',
      start_date: '2024-01-01',
      end_date: '2024-12-31',
      initial_capital: 100000,
      params: { fast: '5', slow: '20' },
    });
    expect(result.current.taskId).toBe('task-1');
  });
});

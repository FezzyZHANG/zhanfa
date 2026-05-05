import { useState, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { submitBacktest, getBacktestTask } from '@/api/client';
import type { BacktestResult, Strategy } from '@/types';

export function useBacktestSubmit(strategies: Strategy[]) {
  const [taskId, setTaskId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const submit = useCallback(async (data: {
    strategy_id: number;
    stock_codes: string[];
    start_date: string;
    end_date: string;
    initial_capital: number;
    params: Record<string, string>;
  }) => {
    setIsSubmitting(true);
    try {
      const strategy = strategies.find((s) => s.id === data.strategy_id);
      const result = await submitBacktest({
        strategy_id: data.strategy_id,
        code: data.stock_codes[0],
        strategy: strategy?.code_ref || strategy?.name || '',
        start_date: data.start_date,
        end_date: data.end_date,
        initial_capital: data.initial_capital,
        params: data.params,
      });
      setTaskId(result.task_id);
      return result;
    } finally {
      setIsSubmitting(false);
    }
  }, [strategies]);

  return { submit, taskId, isSubmitting };
}

export function useBacktestTask(taskId: string | null) {
  const { data } = useQuery<BacktestResult | undefined>({
    queryKey: ['backtest-task', taskId],
    queryFn: () => getBacktestTask(taskId!),
    enabled: !!taskId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === 'pending' || status === 'running') return 2000;
      return false;
    },
  });

  return data;
}

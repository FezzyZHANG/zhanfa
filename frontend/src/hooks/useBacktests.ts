import { useQuery } from '@tanstack/react-query';
import { fetchBacktestResults, fetchBacktestResult } from '@/api/client';

export function useBacktestResults(strategyId?: number) {
  return useQuery({
    queryKey: ['backtests', strategyId],
    queryFn: () => fetchBacktestResults(strategyId),
  });
}

export function useBacktestResult(id: number | string | undefined) {
  return useQuery({
    queryKey: ['backtests', id],
    queryFn: () => fetchBacktestResult(id!),
    enabled: id !== undefined && id !== null && String(id) !== '',
  });
}

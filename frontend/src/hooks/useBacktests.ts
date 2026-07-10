import { useQuery } from '@tanstack/react-query';
import { fetchBacktestResults, fetchBacktestResult } from '@/api/client';

export function useBacktestResults(strategyId?: number) {
  return useQuery({
    queryKey: ['backtests', strategyId],
    queryFn: ({ signal }) => fetchBacktestResults(strategyId, { signal }),
  });
}

export function useBacktestResult(id: number | string | undefined) {
  return useQuery({
    queryKey: ['backtests', id],
    queryFn: ({ signal }) => fetchBacktestResult(id!, { signal }),
    enabled: id !== undefined && id !== null && String(id) !== '',
  });
}

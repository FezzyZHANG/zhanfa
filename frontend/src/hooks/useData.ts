import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchDataStats, fetchStockDataStatus, refreshData, initializeData } from '@/api/client';
import type { RefreshRequest } from '@/types';

export function useDataStats() {
  return useQuery({
    queryKey: ['data-stats'],
    queryFn: fetchDataStats,
  });
}

export function useStockDataStatus(code: string) {
  return useQuery({
    queryKey: ['data-stock-status', code],
    queryFn: () => fetchStockDataStatus(code),
    enabled: !!code,
  });
}

export function useInitializeData() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => initializeData(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['data-stats'] });
    },
  });
}

export function useRefreshData() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: RefreshRequest) => refreshData(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['data-stats'] });
    },
  });
}

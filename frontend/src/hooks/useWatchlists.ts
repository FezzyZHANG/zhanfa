import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  fetchWatchlists,
  createWatchlist,
  renameWatchlist,
  deleteWatchlist,
  addToWatchlist,
  removeFromWatchlist,
  updateItemNotes,
  batchAddItems,
  batchMoveItems,
  batchAddPreview,
  batchDeleteItems,
  fetchWatchlistQuotes,
  searchStocks,
  refreshData,
} from '@/api/client';

export function useWatchlists() {
  return useQuery({
    queryKey: ['watchlists'],
    queryFn: fetchWatchlists,
  });
}

export function useWatchlistQuotes(wlId: number | null) {
  return useQuery({
    queryKey: ['watchlist-quotes', wlId],
    queryFn: () => fetchWatchlistQuotes(wlId!),
    enabled: wlId !== null,
    refetchInterval: 30_000,
  });
}

export function useSearchStocks(q: string) {
  return useQuery({
    queryKey: ['stock-search', q],
    queryFn: () => searchStocks(q),
    enabled: q.length >= 1,
    staleTime: 30_000,
  });
}

export function useCreateWatchlist() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => createWatchlist(name),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['watchlists'] }),
  });
}

export function useRenameWatchlist() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, name }: { id: number; name: string }) => renameWatchlist(id, name),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['watchlists'] }),
  });
}

export function useDeleteWatchlist() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteWatchlist(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['watchlists'] }),
  });
}

export function useAddToWatchlist() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ wlId, code, notes }: { wlId: number; code: string; notes?: string }) =>
      addToWatchlist(wlId, code, notes),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['watchlists'] });
      qc.invalidateQueries({ queryKey: ['watchlist-quotes'] });
    },
  });
}

export function useRemoveFromWatchlist() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ wlId, code }: { wlId: number; code: string }) => removeFromWatchlist(wlId, code),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['watchlists'] });
      qc.invalidateQueries({ queryKey: ['watchlist-quotes'] });
    },
  });
}

export function useUpdateItemNotes() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ wlId, code, notes }: { wlId: number; code: string; notes: string | null }) =>
      updateItemNotes(wlId, code, notes),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['watchlists'] });
      qc.invalidateQueries({ queryKey: ['watchlist-quotes'] });
    },
  });
}

export function useBatchAddItems() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ wlId, codes }: { wlId: number; codes: string[] }) => batchAddItems(wlId, codes),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['watchlists'] });
      qc.invalidateQueries({ queryKey: ['watchlist-quotes'] });
    },
  });
}

export function useBatchMoveItems() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ fromWlId, toWlId, codes }: { fromWlId: number; toWlId: number; codes: string[] }) =>
      batchMoveItems(fromWlId, toWlId, codes),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['watchlists'] });
      qc.invalidateQueries({ queryKey: ['watchlist-quotes'] });
    },
  });
}

export function useBatchAddPreview() {
  return useMutation({
    mutationFn: ({ wlId, codes }: { wlId: number; codes: string[] }) => batchAddPreview(wlId, codes),
  });
}

export function useBatchDeleteItems() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ wlId, codes }: { wlId: number; codes: string[] }) => batchDeleteItems(wlId, codes),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['watchlists'] });
      qc.invalidateQueries({ queryKey: ['watchlist-quotes'] });
    },
  });
}

export function useRefreshWatchlistData() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (codes: string[]) => refreshData({ codes, freq: 'daily', force: false }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['watchlist-quotes'] });
    },
  });
}

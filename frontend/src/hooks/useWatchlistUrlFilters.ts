import { useSearch, useNavigate } from '@tanstack/react-router';
import type { WatchlistSearchParams } from '@/router';
import type { QuoteItem } from '@/types';

export type SortKey = 'code' | 'name' | 'latest_price' | 'change_pct' | 'pe' | 'pb' | 'dividend_yield';
export type SortDir = 'asc' | 'desc';

export function useWatchlistUrlFilters() {
  const search = useSearch({ from: '/watchlist' }) as WatchlistSearchParams;
  const navigate = useNavigate({ from: '/watchlist' });

  const sortKey = (search.sortKey || 'code') as SortKey;
  const sortDir = (search.sortDir || 'asc') as SortDir;
  const searchText = search.search || '';
  const peMin = search.peMin ? parseFloat(search.peMin) : undefined;
  const peMax = search.peMax ? parseFloat(search.peMax) : undefined;
  const changeDir = search.changeDir || '';

  const setSort = (key: SortKey, dir: SortDir) => {
    navigate({
      search: { ...search, sortKey: key, sortDir: dir } as WatchlistSearchParams,
      replace: true,
    } as Parameters<typeof navigate>[0]);
  };

  const setSearchText = (text: string) => {
    navigate({
      search: { ...search, search: text || '' } as WatchlistSearchParams,
      replace: true,
    } as Parameters<typeof navigate>[0]);
  };

  const setPeRange = (min: string, max: string) => {
    navigate({
      search: { ...search, peMin: min, peMax: max } as WatchlistSearchParams,
      replace: true,
    } as Parameters<typeof navigate>[0]);
  };

  const setChangeFilter = (dir: string) => {
    navigate({
      search: { ...search, changeDir: dir } as WatchlistSearchParams,
      replace: true,
    } as Parameters<typeof navigate>[0]);
  };

  const applyFilters = (items: QuoteItem[]): QuoteItem[] => {
    let filtered = [...items];

    if (searchText) {
      const kw = searchText.toLowerCase();
      filtered = filtered.filter(
        (item) =>
          item.code.toLowerCase().includes(kw) ||
          (item.name || '').toLowerCase().includes(kw)
      );
    }

    if (peMin !== undefined && !isNaN(peMin)) {
      filtered = filtered.filter((item) => item.pe != null && item.pe >= peMin);
    }
    if (peMax !== undefined && !isNaN(peMax)) {
      filtered = filtered.filter((item) => item.pe != null && item.pe <= peMax);
    }

    if (changeDir === 'up') {
      filtered = filtered.filter((item) => item.change_pct != null && item.change_pct > 0);
    } else if (changeDir === 'down') {
      filtered = filtered.filter((item) => item.change_pct != null && item.change_pct < 0);
    }

    return filtered;
  };

  return {
    sortKey,
    sortDir,
    searchText,
    peMin,
    peMax,
    changeDir,
    setSort,
    setSearchText,
    setPeRange,
    setChangeFilter,
    applyFilters,
  };
}

import { useQuery } from '@tanstack/react-query';
import { fetchStocks, fetchStock, fetchKline, fetchFinancials } from '@/api/client';

export function useStocks() {
  return useQuery({
    queryKey: ['stocks'],
    queryFn: ({ signal }) => fetchStocks({ signal }),
  });
}

export function useStock(code: string) {
  return useQuery({
    queryKey: ['stocks', code],
    queryFn: ({ signal }) => fetchStock(code, { signal }),
    enabled: !!code,
  });
}

export function useKline(code: string, start?: string, end?: string, freq?: string) {
  return useQuery({
    queryKey: ['kline', code, start, end, freq],
    queryFn: ({ signal }) => fetchKline(code, start, end, freq, { signal }),
    enabled: !!code,
  });
}

export function useFinancials(code: string) {
  return useQuery({
    queryKey: ['financials', code],
    queryFn: ({ signal }) => fetchFinancials(code, { signal }),
    enabled: !!code,
  });
}

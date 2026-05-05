import { useQuery } from '@tanstack/react-query';
import { fetchStocks, fetchStock, fetchKline, fetchFinancials } from '@/api/client';

export function useStocks() {
  return useQuery({
    queryKey: ['stocks'],
    queryFn: fetchStocks,
  });
}

export function useStock(code: string) {
  return useQuery({
    queryKey: ['stocks', code],
    queryFn: () => fetchStock(code),
    enabled: !!code,
  });
}

export function useKline(code: string, start?: string, end?: string, freq?: string) {
  return useQuery({
    queryKey: ['kline', code, start, end, freq],
    queryFn: () => fetchKline(code, start, end, freq),
    enabled: !!code,
  });
}

export function useFinancials(code: string) {
  return useQuery({
    queryKey: ['financials', code],
    queryFn: () => fetchFinancials(code),
    enabled: !!code,
  });
}

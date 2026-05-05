import { useMemo } from 'react';
import { useFinancials } from './useStocks';
import type { FinancialData } from '@/types';

export function useFinancialData(code: string) {
  const query = useFinancials(code);

  const sortedData = useMemo(() => {
    if (!query.data) return [];
    return [...query.data].sort((a, b) => a.report_date.localeCompare(b.report_date));
  }, [query.data]);

  const latest = sortedData[sortedData.length - 1] as FinancialData | undefined;
  const previous = sortedData[sortedData.length - 2] as FinancialData | undefined;

  const yoyGrowth = useMemo(() => {
    if (!latest || !previous) return undefined;
    return {
      net_profit: previous.net_profit ? (latest.net_profit - previous.net_profit) / Math.abs(previous.net_profit) : 0,
      revenue: previous.revenue ? (latest.revenue - previous.revenue) / Math.abs(previous.revenue) : 0,
      eps: previous.eps ? (latest.eps - previous.eps) / Math.abs(previous.eps) : 0,
      roe: latest.roe - previous.roe,
    };
  }, [latest, previous]);

  const recentQuarters = useMemo(() => sortedData.slice(-4), [sortedData]);

  return {
    ...query,
    sortedData,
    latest,
    previous,
    yoyGrowth,
    recentQuarters,
  };
}

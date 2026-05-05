import { useState, useEffect } from 'react';
import { useDataStats, useRefreshData, useInitializeData } from '@/hooks/useData';
import { Button } from '@/components/ui/Button';
import { DataStatsCards } from '@/components/data/DataStatsCards';
import { RefreshButton } from '@/components/data/RefreshButton';
import { DataCoverageChart } from '@/components/data/DataCoverageChart';
import { StockDataTable } from '@/components/data/StockDataTable';
import { fetchStockDataStatus } from '@/api/client';
import type { StockDataStatus } from '@/types';

const WATCHED_CODES = ['600519', '000858', '300750', '600036', '000001'];

export function DataPage() {
  const { data: stats, isLoading: statsLoading, refetch: refetchStats } = useDataStats();
  const refreshMutation = useRefreshData();
  const initMutation = useInitializeData();

  const [stockStatuses, setStockStatuses] = useState<StockDataStatus[]>([]);
  const [tableLoading, setTableLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setTableLoading(true);
      const results: StockDataStatus[] = [];
      for (const code of WATCHED_CODES) {
        try {
          const s = await fetchStockDataStatus(code);
          if (s && !cancelled) results.push(s);
        } catch {
          // skip failed fetches
        }
      }
      if (!cancelled) {
        setStockStatuses(results);
        setTableLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [stats?.cache.stock_count]);

  const handleRefresh = async (force: boolean) => {
    const result = await refreshMutation.mutateAsync({
      codes: null,
      freq: 'daily',
      force,
      discover_new: true,
      max_new: 50,
    });
    refetchStats();
    return result;
  };

  const defaultStats = stats ?? {
    cache: {
      stock_count: 0,
      total_rows: 0,
      storage_bytes: 0,
      date_range_start: null,
      date_range_end: null,
      freq_stats: {},
    },
    database: {
      stock_count: 0,
      financial_count: 0,
      watchlist_count: 0,
      strategy_count: 0,
      backtest_count: 0,
    },
  };

  const totalStocks = defaultStats.database.stock_count || 5000;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">数据管理</h1>
          <p className="text-sm text-muted-foreground mt-1">
            查看缓存和数据库状态，管理数据刷新
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => initMutation.mutate()}
            disabled={initMutation.isPending}
          >
            {initMutation.isPending ? '初始化中...' : '初始化数据'}
          </Button>
          <RefreshButton onRefresh={handleRefresh} />
        </div>
      </div>

      {initMutation.data && (
        <div className="rounded-xl border border-green-200 bg-green-50 dark:bg-green-950 p-4 text-sm text-green-700 dark:text-green-300">
          {initMutation.data.message}
        </div>
      )}

      {initMutation.isError && (
        <div className="rounded-xl border border-red-200 bg-red-50 dark:bg-red-950 p-4 text-sm text-red-600">
          {initMutation.error instanceof Error ? initMutation.error.message : '初始化失败'}
        </div>
      )}

      {!statsLoading && stats && stats.cache.stock_count === 0 && stats.database.stock_count === 0 && !initMutation.data ? (
        <div className="rounded-xl border border-border bg-card p-6 text-center space-y-3">
          <p className="text-muted-foreground">尚未初始化数据</p>
          <p className="text-xs text-muted-foreground">
            请先点击「初始化数据」导入全 A 股列表，再使用「抓取至今」拉取日线数据。
          </p>
          <Button
            onClick={() => initMutation.mutate()}
            disabled={initMutation.isPending}
          >
            {initMutation.isPending ? '初始化中...' : '开始初始化数据'}
          </Button>
        </div>
      ) : null}

      {statsLoading && !stats ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="rounded-xl border border-border bg-card p-4 animate-pulse">
              <div className="h-3 bg-muted rounded w-16 mb-2" />
              <div className="h-6 bg-muted rounded w-24 mb-1" />
              <div className="h-3 bg-muted rounded w-32" />
            </div>
          ))}
        </div>
      ) : (
        <>
          <DataStatsCards stats={defaultStats} totalStocks={totalStocks} />
          <DataCoverageChart stats={defaultStats} />
          <StockDataTable data={stockStatuses} loading={tableLoading} />
        </>
      )}
    </div>
  );
}

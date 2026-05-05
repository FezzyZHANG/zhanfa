import type { DataStats } from '@/types';
import { Card } from '@/components/ui/Card';

function fmtBytes(bytes: number): string {
  if (bytes >= 1e9) return `${(bytes / 1e9).toFixed(1)} GB`;
  if (bytes >= 1e6) return `${(bytes / 1e6).toFixed(1)} MB`;
  if (bytes >= 1e3) return `${(bytes / 1e3).toFixed(1)} KB`;
  return `${bytes} B`;
}

function fmtNum(n: number): string {
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  if (n >= 1e4) return `${(n / 1e4).toFixed(1)}万`;
  return n.toLocaleString();
}

interface Props {
  stats: DataStats;
  totalStocks: number;
}

export function DataStatsCards({ stats, totalStocks }: Props) {
  const { cache, database } = stats;
  const coveragePct = totalStocks > 0 ? ((cache.stock_count / totalStocks) * 100).toFixed(1) : '0';

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {/* 日线缓存 */}
        <Card className="p-4">
          <p className="text-xs text-muted-foreground mb-1">日线缓存</p>
          <p className="text-xl font-bold text-foreground">
            {cache.stock_count.toLocaleString()}
            <span className="text-sm font-normal text-muted-foreground ml-1">
              / {totalStocks.toLocaleString()}
            </span>
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            覆盖率 {coveragePct}% · {fmtNum(cache.total_rows)} 行 · {fmtBytes(cache.storage_bytes)}
          </p>
        </Card>

        {/* 数据覆盖 */}
        <Card className="p-4">
          <p className="text-xs text-muted-foreground mb-1">数据覆盖</p>
          <p className="text-xl font-bold text-foreground">
            {cache.date_range_start ? cache.date_range_start.slice(0, 10) : '—'}
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            至 {cache.date_range_end ? cache.date_range_end.slice(0, 10) : '—'}
          </p>
        </Card>

        {/* 财务数据 */}
        <Card className="p-4">
          <p className="text-xs text-muted-foreground mb-1">财务数据</p>
          <p className="text-xl font-bold text-foreground">
            {database.financial_count.toLocaleString()}
            <span className="text-sm font-normal text-muted-foreground ml-1">条</span>
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            覆盖 {(cache.freq_stats?.financial ?? 0).toLocaleString()} 只股票
          </p>
        </Card>

        {/* 数据库 */}
        <Card className="p-4">
          <p className="text-xs text-muted-foreground mb-1">数据库</p>
          <div className="text-xs text-muted-foreground mt-1 space-y-0.5">
            <p>股票 {database.stock_count.toLocaleString()}</p>
            <p>策略 {database.strategy_count} · 回测 {database.backtest_count}</p>
            <p>自选组 {database.watchlist_count}</p>
          </div>
        </Card>
      </div>
    </div>
  );
}

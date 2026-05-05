import { Skeleton } from '@/components/ui/Skeleton';
import { formatNumber, formatPercent } from '@/lib/utils';
import type { FinancialData } from '@/types';

interface MetricCardsProps {
  latest: FinancialData;
  previous?: FinancialData;
  yoyGrowth?: {
    net_profit: number;
    revenue: number;
    eps: number;
    roe: number;
  };
  recentQuarters: FinancialData[];
  isLoading?: boolean;
}

function TrendBadge({ value, invert }: { value: number; invert?: boolean }) {
  const isPositive = invert ? value < 0 : value > 0;
  const isNeutral = Math.abs(value) < 0.001;
  if (isNeutral) return <span className="text-xs text-muted-foreground">持平</span>;
  return (
    <span className={`text-xs font-medium ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
      {isPositive ? '↑' : '↓'} {Math.abs(value * 100).toFixed(1)}%
    </span>
  );
}

interface MetricCardProps {
  label: string;
  value: string;
  sub?: string;
  trend?: number;
  invertTrend?: boolean;
}

function MetricCard({ label, value, sub, trend, invertTrend }: MetricCardProps) {
  return (
    <div className="flex flex-col gap-1 p-4 rounded-lg bg-muted/40">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className="text-xl font-bold tracking-tight">{value}</span>
      <div className="flex items-center gap-2">
        {trend !== undefined && <TrendBadge value={trend} invert={invertTrend} />}
        {sub && <span className="text-xs text-muted-foreground">{sub}</span>}
      </div>
    </div>
  );
}

export function MetricCards({ latest, previous, yoyGrowth, isLoading }: MetricCardsProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-24" />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
      <MetricCard
        label="净利润(亿)"
        value={formatNumber(latest.net_profit / 100_000_000)}
        trend={yoyGrowth?.net_profit}
      />
      <MetricCard
        label="营业收入(亿)"
        value={formatNumber(latest.revenue / 100_000_000)}
        trend={yoyGrowth?.revenue}
      />
      <MetricCard label="EPS" value={latest.eps.toFixed(2)} trend={yoyGrowth?.eps} />
      <MetricCard
        label="ROE"
        value={formatPercent(latest.roe)}
        trend={yoyGrowth?.roe}
      />
      <MetricCard
        label="资产负债率"
        value={formatPercent(latest.debt_ratio)}
        trend={previous ? latest.debt_ratio - previous.debt_ratio : undefined}
        invertTrend
      />
      <MetricCard
        label="股息率"
        value={formatPercent(latest.dividend_yield)}
        trend={previous ? latest.dividend_yield - previous.dividend_yield : undefined}
      />
    </div>
  );
}

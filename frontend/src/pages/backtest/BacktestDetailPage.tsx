import { useParams } from '@tanstack/react-router';
import { useBacktestResult } from '@/hooks/useBacktests';
import { BacktestMetrics } from '@/components/backtest/BacktestMetrics';
import { EquityCurve } from '@/components/backtest/EquityCurve';
import { DrawdownCurve } from '@/components/backtest/DrawdownCurve';
import { YearlyReturns } from '@/components/backtest/YearlyReturns';
import { MonthlyHeatmap } from '@/components/backtest/MonthlyHeatmap';
import { TradeTable } from '@/components/backtest/TradeTable';
import { Skeleton } from '@/components/ui/Skeleton';
import { ErrorBoundary } from '@/components/ErrorBoundary';

export function BacktestDetailPage() {
  const { backtestId } = useParams({ strict: false });
  const { data: result, isLoading } = useBacktestResult(backtestId ?? '');

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-20 rounded-xl" />
          ))}
        </div>
        <Skeleton className="h-80 rounded-xl" />
        <Skeleton className="h-48 rounded-xl" />
        <Skeleton className="h-64 rounded-xl" />
      </div>
    );
  }

  if (!result) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        回测结果不存在
      </div>
    );
  }

  if (result.status === 'pending' || result.status === 'running') {
    return (
      <div className="text-center py-12">
        <div className="inline-flex items-center gap-2 text-muted-foreground">
          <span className="animate-spin w-4 h-4 border-2 border-primary border-t-transparent rounded-full" />
          {result.status === 'pending' ? '等待回测开始...' : '回测运行中...'}
        </div>
      </div>
    );
  }

  if (result.status === 'failed') {
    return (
      <div className="text-center py-12 text-red-500">
        回测失败，请重试
      </div>
    );
  }

  const { metrics, equity_curve, drawdown_curve, benchmark_curve, yearly_returns, monthly_returns, trades } = result;

  return (
    <div className="space-y-6">
      <div className="mb-2">
        <h1 className="text-2xl font-bold tracking-tight mb-1">回测结果</h1>
        <p className="text-muted-foreground text-sm">
          {result.strategy_name || `策略 #${result.strategy_id}`} · {result.start_date} 至 {result.end_date} ·{' '}
          标的: {result.stock_codes.join(', ')}
        </p>
      </div>

      <BacktestMetrics metrics={metrics} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="lg:col-span-2">
          <ErrorBoundary
            label="EquityCurve"
            resetKey={result.id}
            fallback={
              <div role="alert" className="rounded-xl border border-border bg-card p-6 text-sm text-muted-foreground">
                净值曲线加载失败
              </div>
            }
          >
            <EquityCurve
              equity={equity_curve}
              benchmark={benchmark_curve}
              height={400}
            />
          </ErrorBoundary>
        </div>
        <DrawdownCurve drawdown={drawdown_curve} height={220} />
        <YearlyReturns data={yearly_returns} height={220} />
      </div>

      <MonthlyHeatmap data={monthly_returns} />

      <TradeTable trades={trades} />
    </div>
  );
}

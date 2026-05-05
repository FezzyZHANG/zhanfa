import { useBacktestResults } from '@/hooks/useBacktests';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import { formatPercent } from '@/lib/utils';
import { useNavigate } from '@tanstack/react-router';

const STATUS_MAP: Record<string, { label: string; className: string }> = {
  pending: { label: '等待中', className: 'bg-yellow-100 text-yellow-800' },
  running: { label: '运行中', className: 'bg-blue-100 text-blue-800' },
  done: { label: '已完成', className: 'bg-green-100 text-green-800' },
  failed: { label: '失败', className: 'bg-red-100 text-red-800' },
};

export function BacktestListPage() {
  const { data: results, isLoading } = useBacktestResults();
  const navigate = useNavigate();

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-32 rounded-xl" />
        ))}
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight mb-2">回测结果</h1>
        <p className="text-muted-foreground">查看历史回测绩效指标与交易记录</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {results?.map((bt) => {
          const s = STATUS_MAP[bt.status] || STATUS_MAP.pending;
          return (
            <Card
              key={bt.id}
              className="cursor-pointer hover:shadow-md transition-shadow"
              onClick={() => navigate({ to: '/backtest/$backtestId', params: { backtestId: String(bt.id) } })}
            >
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">
                    {bt.strategy_name || `策略 #${bt.strategy_id}`}
                  </CardTitle>
                  <Badge className={s.className}>{s.label}</Badge>
                </div>
                <CardDescription>
                  {bt.start_date} ~ {bt.end_date} · {bt.stock_codes.join(', ')}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <p className="text-muted-foreground text-xs">总收益</p>
                    <p className={`font-semibold ${(bt.metrics.total_return ?? 0) >= 0 ? 'text-green-600' : 'text-red-500'}`}>
                      {bt.metrics.total_return != null ? formatPercent(bt.metrics.total_return) : '--'}
                    </p>
                  </div>
                  <div>
                    <p className="text-muted-foreground text-xs">夏普</p>
                    <p className="font-semibold">{bt.metrics.sharpe != null ? bt.metrics.sharpe.toFixed(2) : '--'}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground text-xs">最大回撤</p>
                    <p className="font-semibold text-red-500">
                      {bt.metrics.max_drawdown != null ? formatPercent(bt.metrics.max_drawdown) : '--'}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
        {results?.length === 0 && (
          <p className="text-center text-muted-foreground col-span-full py-12">暂无回测数据</p>
        )}
      </div>
    </div>
  );
}

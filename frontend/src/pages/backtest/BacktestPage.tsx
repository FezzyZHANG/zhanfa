import { useEffect, useState } from 'react';
import { useNavigate } from '@tanstack/react-router';
import { useStrategies } from '@/hooks/useStrategies';
import { useBacktestResults } from '@/hooks/useBacktests';
import { useStocks } from '@/hooks/useStocks';
import { useBacktestSubmit, useBacktestTask } from '@/hooks/useBacktest';
import { BacktestForm } from '@/components/backtest/BacktestForm';
import { CompareView } from '@/components/backtest/CompareView';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
import { formatPercent } from '@/lib/utils';
import type { Strategy } from '@/types';

const STATUS_MAP: Record<string, { label: string; className: string }> = {
  pending: { label: '等待中', className: 'bg-yellow-100 text-yellow-800' },
  running: { label: '运行中', className: 'bg-blue-100 text-blue-800' },
  done: { label: '已完成', className: 'bg-green-100 text-green-800' },
  failed: { label: '失败', className: 'bg-red-100 text-red-800' },
};

export function BacktestPage() {
  const navigate = useNavigate();
  const { data: strategiesData } = useStrategies();
  const { data: backtests, isLoading: btLoading } = useBacktestResults();
  const { data: stocks } = useStocks();
  const strategies = Array.isArray(strategiesData) ? (strategiesData as Strategy[]) : [];
  const { submit, taskId, isSubmitting } = useBacktestSubmit(strategies);
  const pollResult = useBacktestTask(taskId);
  const [showCompare, setShowCompare] = useState(false);

  useEffect(() => {
    if (pollResult?.status === 'done' && taskId) {
      navigate({ to: '/backtest/$backtestId', params: { backtestId: String(pollResult.id) } });
    }
  }, [navigate, pollResult?.id, pollResult?.status, taskId]);

  const completedBacktests = backtests?.filter((b) => b.status === 'done') || [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight mb-2">回测</h1>
        <p className="text-muted-foreground">运行策略回测，分析绩效指标与交易记录</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <BacktestForm
            strategies={strategies}
            stocks={stocks?.map((s) => ({ code: s.code, name: s.name })) || []}
            onSubmit={submit}
            isSubmitting={isSubmitting}
          />
        </div>

        <div className="lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">历史回测</h2>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={completedBacktests.length < 2}
                onClick={() => setShowCompare(!showCompare)}
              >
                {showCompare ? '列表视图' : '对比视图'}
              </Button>
            </div>
          </div>

          {btLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-28 rounded-xl" />
              ))}
            </div>
          ) : showCompare ? (
            <CompareView results={completedBacktests} />
          ) : backtests && backtests.length > 0 ? (
            <div className="space-y-3">
              {backtests.map((bt) => {
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
                    {bt.status === 'done' && (
                      <CardContent>
                        <div className="grid grid-cols-4 gap-4 text-sm">
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
                            <p className="font-semibold text-red-500">{bt.metrics.max_drawdown != null ? formatPercent(bt.metrics.max_drawdown) : '--'}</p>
                          </div>
                          <div>
                            <p className="text-muted-foreground text-xs">胜率</p>
                            <p className="font-semibold">{bt.metrics.win_rate != null ? formatPercent(bt.metrics.win_rate) : '--'}</p>
                          </div>
                        </div>
                      </CardContent>
                    )}
                  </Card>
                );
              })}
            </div>
          ) : (
            <div className="text-center py-12 text-muted-foreground border rounded-xl">
              暂无回测记录，填写左侧表单开始回测
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

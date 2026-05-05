import { useParams } from '@tanstack/react-router';
import { useStrategy } from '@/hooks/useStrategies';
import { useBacktestResults } from '@/hooks/useBacktests';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
import { StrategyParams } from '@/components/strategy/StrategyParams';
import { getCategoryLabel, getCategoryColor, formatPercent } from '@/lib/utils';
import { useNavigate } from '@tanstack/react-router';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export function StrategyDetailPage() {
  const { strategyId } = useParams({ strict: false });
  const id = Number(strategyId);
  const { data: strategy, isLoading } = useStrategy(id);
  const { data: backtests } = useBacktestResults(id);
  const navigate = useNavigate();

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-48" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (!strategy) {
    return <div className="text-center py-12 text-muted-foreground">策略不存在</div>;
  }

  return (
    <div>
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <h1 className="text-3xl font-bold tracking-tight">{strategy.name}</h1>
          <Badge className={getCategoryColor(strategy.category)}>
            {getCategoryLabel(strategy.category)}
          </Badge>
        </div>
        {strategy.code_ref && (
          <p className="text-xs text-muted-foreground mb-3 font-mono">{strategy.code_ref}</p>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>策略描述</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="prose prose-sm dark:prose-invert max-w-none
                prose-headings:text-foreground prose-p:text-muted-foreground
                prose-li:text-muted-foreground prose-strong:text-foreground
                prose-a:text-primary">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {strategy.description || '暂无描述'}
                </ReactMarkdown>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>策略参数</CardTitle>
            </CardHeader>
            <CardContent>
              <StrategyParams params={strategy.params} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>基本信息</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="space-y-2">
                <div className="flex justify-between py-2 border-b border-border">
                  <dt className="text-sm text-muted-foreground">创建时间</dt>
                  <dd className="text-sm font-medium">{new Date(strategy.created_at).toLocaleDateString('zh-CN')}</dd>
                </div>
                <div className="flex justify-between py-2 border-b border-border">
                  <dt className="text-sm text-muted-foreground">最后更新</dt>
                  <dd className="text-sm font-medium">{new Date(strategy.updated_at).toLocaleDateString('zh-CN')}</dd>
                </div>
                <div className="flex justify-between py-2">
                  <dt className="text-sm text-muted-foreground">回测次数</dt>
                  <dd className="text-sm font-medium">{strategy.backtest_count ?? backtests?.length ?? 0}</dd>
                </div>
              </dl>
            </CardContent>
          </Card>

          <Button
            className="w-full"
            onClick={() => navigate({ to: '/backtest', search: { strategy: String(strategy.id), ...Object.fromEntries(Object.entries(strategy.params).map(([k, v]) => [k, String(v.default)])) } })}
          >
            运行回测
          </Button>
        </div>
      </div>

      <div>
        <h2 className="text-xl font-semibold mb-4">回测记录</h2>
        {!backtests || backtests.length === 0 ? (
          <div className="text-center py-12 border rounded-lg border-border">
            <p className="text-muted-foreground mb-4">暂无回测记录</p>
            <Button
              variant="outline"
              onClick={() => navigate({ to: '/backtest' })}
            >
              创建首次回测
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {backtests.map((bt) => (
              <Card
                key={bt.id}
                className="cursor-pointer hover:shadow-md transition-shadow"
                onClick={() => navigate({ to: '/backtest/$backtestId', params: { backtestId: String(bt.id) } })}
              >
                <CardHeader>
                  <CardTitle className="text-base">{bt.start_date} ~ {bt.end_date}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground mb-3">
                    {bt.stock_codes.join(', ')}
                  </p>
                  <div className="grid grid-cols-2 gap-y-2 text-sm">
                    <span className="text-muted-foreground">总收益</span>
                    <span className="font-medium text-right text-green-600">
                      {bt.metrics.total_return != null ? formatPercent(bt.metrics.total_return) : '--'}
                    </span>
                    <span className="text-muted-foreground">夏普比率</span>
                    <span className="font-medium text-right">{bt.metrics.sharpe != null ? bt.metrics.sharpe.toFixed(2) : '--'}</span>
                    <span className="text-muted-foreground">最大回撤</span>
                    <span className="font-medium text-right text-red-500">
                      {bt.metrics.max_drawdown != null ? formatPercent(bt.metrics.max_drawdown) : '--'}
                    </span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

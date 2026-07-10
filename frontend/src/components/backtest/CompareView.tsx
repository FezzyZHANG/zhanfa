import { useState } from 'react';
import type { BacktestResult } from '@/types';
import { EquityCurve } from './EquityCurve';
import { Card } from '@/components/ui/Card';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { formatPercent } from '@/lib/utils';

interface CompareViewProps {
  results: BacktestResult[];
}

const METRICS_KEYS: { key: keyof BacktestResult['metrics']; label: string; format: 'pct' | 'num' }[] = [
  { key: 'total_return', label: '总收益', format: 'pct' },
  { key: 'ann_return', label: '年化收益', format: 'pct' },
  { key: 'sharpe', label: '夏普比率', format: 'num' },
  { key: 'max_drawdown', label: '最大回撤', format: 'pct' },
  { key: 'win_rate', label: '胜率', format: 'pct' },
  { key: 'calmar', label: '卡玛比率', format: 'num' },
];

export function CompareView({ results }: CompareViewProps) {
  const [selected, setSelected] = useState<Set<BacktestResult['id']>>(() => {
    const s = new Set<BacktestResult['id']>();
    results.slice(0, 3).forEach((r) => s.add(r.id));
    return s;
  });

  const toggle = (id: BacktestResult['id']) => {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id); else next.add(id);
    setSelected(next);
  };

  const selectedResults = results.filter((r) => selected.has(r.id));
  const comparisons = selectedResults.map((r, i) => ({
    label: r.strategy_name || `策略 #${r.strategy_id}`,
    data: r.equity_curve,
    colorIndex: i,
  }));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-2">
        {results.map((r) => (
          <button
            key={r.id}
            onClick={() => toggle(r.id)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
              selected.has(r.id)
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted text-muted-foreground hover:bg-muted/80'
            }`}
          >
            {r.strategy_name || `策略 #${r.strategy_id}`}
            {selected.has(r.id) ? ' ✓' : ''}
          </button>
        ))}
      </div>

      <ErrorBoundary
        label="Compare EquityCurve"
        resetKey={selectedResults.map((r) => r.id).join(',')}
        fallback={
          <div role="alert" className="rounded-xl border border-border bg-card p-6 text-sm text-muted-foreground">
            净值曲线加载失败
          </div>
        }
      >
        <EquityCurve
          equity={results[0].equity_curve}
          comparisons={comparisons.filter((_, i) => i > 0)}
          height={400}
        />
      </ErrorBoundary>

      <Card>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-3 px-4 font-medium text-muted-foreground">指标</th>
                {selectedResults.map((r) => (
                  <th key={r.id} className="text-right py-3 px-4 font-medium">
                    {r.strategy_name || `#${r.strategy_id}`}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {METRICS_KEYS.map(({ key, label, format }) => (
                <tr key={key} className="border-b border-border">
                  <td className="py-2 px-4 text-muted-foreground">{label}</td>
                  {selectedResults.map((r) => {
                    const v = r.metrics[key] as number;
                    if (v === undefined) return <td key={r.id} className="text-right py-2 px-4">-</td>;
                    const display = format === 'pct' ? formatPercent(v) : v.toFixed(2);
                    let cls = 'text-right py-2 px-4 font-mono ';
                    if (key === 'max_drawdown') {
                      cls += v > -0.1 ? 'text-green-600' : v > -0.2 ? 'text-yellow-600' : 'text-red-500';
                    } else {
                      cls += v >= 0 ? 'text-green-600' : 'text-red-500';
                    }
                    return <td key={r.id} className={cls}>{display}</td>;
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

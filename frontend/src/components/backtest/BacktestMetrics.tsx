import type { BacktestMetrics as BM } from '@/types';
import { Card } from '@/components/ui/Card';

const METRICS_CONFIG: { key: keyof BM; label: string; format: 'pct' | 'num' | 'ratio' }[] = [
  { key: 'total_return', label: '总收益率', format: 'pct' },
  { key: 'ann_return', label: '年化收益率', format: 'pct' },
  { key: 'ann_volatility', label: '年化波动率', format: 'pct' },
  { key: 'sharpe', label: '夏普比率', format: 'ratio' },
  { key: 'sortino', label: '索提诺比率', format: 'ratio' },
  { key: 'max_drawdown', label: '最大回撤', format: 'pct' },
  { key: 'calmar', label: '卡玛比率', format: 'ratio' },
  { key: 'win_rate', label: '胜率', format: 'pct' },
];

function fmtPercent(v: number): string {
  return `${(v * 100).toFixed(2)}%`;
}

function fmtNum(v: number): string {
  return v.toFixed(2);
}

function getClass(key: string, v: number): string {
  if (key === 'max_drawdown' || key === 'ann_volatility') {
    return v > -0.1 ? 'text-green-600' : v > -0.2 ? 'text-yellow-600' : 'text-red-500';
  }
  if (key === 'win_rate') return v >= 0.5 ? 'text-green-600' : 'text-yellow-600';
  return v >= 0 ? 'text-green-600' : 'text-red-500';
}

export function BacktestMetrics({ metrics }: { metrics: BM }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {METRICS_CONFIG.map(({ key, label, format }) => {
        const value = metrics[key];
        if (value === undefined || value === null) return null;
        const display = format === 'pct' ? fmtPercent(value as number) : fmtNum(value as number);
        return (
          <Card key={key} className="p-4">
            <p className="text-xs text-muted-foreground mb-1">{label}</p>
            <p className={`text-xl font-bold ${getClass(key, value as number)}`}>{display}</p>
          </Card>
        );
      })}
    </div>
  );
}

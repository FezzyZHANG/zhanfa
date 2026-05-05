import type { KlineData } from '@/types';
import { formatNumber } from '@/lib/utils';

interface ChartCrosshairProps {
  data: KlineData | null;
  visible: boolean;
  x: number;
  y: number;
  containerWidth: number;
}

export function ChartCrosshair({ data, visible, x, y, containerWidth }: ChartCrosshairProps) {
  if (!visible || !data) return null;

  const isUp = data.close >= data.open;
  const change = data.close - data.open;
  const changePct = data.open !== 0 ? (change / data.open) * 100 : 0;

  const left = x + 120 > containerWidth ? x - 180 : x + 20;

  return (
    <div
      className="absolute z-50 pointer-events-none bg-card border border-border rounded-lg shadow-lg p-3 text-xs font-mono"
      style={{ left, top: y - 60 }}
    >
      <div className="text-muted-foreground mb-1">{data.date}</div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-0.5">
        <span className="text-muted-foreground">开</span>
        <span>{data.open.toFixed(2)}</span>
        <span className="text-muted-foreground">高</span>
        <span className="text-red-500">{data.high.toFixed(2)}</span>
        <span className="text-muted-foreground">低</span>
        <span className="text-green-500">{data.low.toFixed(2)}</span>
        <span className="text-muted-foreground">收</span>
        <span className={isUp ? 'text-red-500' : 'text-green-500'}>
          {data.close.toFixed(2)}
        </span>
        <span className="text-muted-foreground">量</span>
        <span>{formatNumber(data.volume)}</span>
        <span className="text-muted-foreground">涨跌</span>
        <span className={isUp ? 'text-red-500' : 'text-green-500'}>
          {change >= 0 ? '+' : ''}{change.toFixed(2)} ({changePct >= 0 ? '+' : ''}{changePct.toFixed(2)}%)
        </span>
      </div>
    </div>
  );
}

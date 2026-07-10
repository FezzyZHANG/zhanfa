import { createChart, LineSeries, type IChartApi, type LineData, type Time } from 'lightweight-charts';
import { useEffect, useRef } from 'react';

interface SparklineProps {
  data: { time: string; value: number }[];
  width?: number;
  height?: number;
  color?: string;
}

export function Sparkline({ data, width = 80, height = 32, color }: SparklineProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!containerRef.current || data.length < 2) return;

    const chart = createChart(containerRef.current, {
      width,
      height,
      layout: { background: { color: 'transparent' } },
      grid: { vertLines: { visible: false }, horzLines: { visible: false } },
      rightPriceScale: { visible: false },
      timeScale: { visible: false },
      crosshair: { vertLine: { visible: false }, horzLine: { visible: false } },
      handleScroll: false,
      handleScale: false,
    });

    const series = chart.addSeries(LineSeries, {
      color: color || '#3b82f6',
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
    });

    const lineData: LineData[] = data.map((d) => ({ time: d.time as Time, value: d.value }));
    series.setData(lineData);

    chart.timeScale().fitContent();
    chartRef.current = chart;

    return () => chart.remove();
  }, [data, width, height, color]);

  return <div ref={containerRef} />;
}

import type { QuoteItem } from '@/types';
import { formatNumber, formatPercent } from '@/lib/utils';
import { useNavigate } from '@tanstack/react-router';
import { Button } from '@/components/ui/Button';
import { DataStatusBadge } from './DataStatusBadge';

interface WatchlistCardsProps {
  quotes: QuoteItem[];
  onRemove: (code: string) => void;
}

export function WatchlistCards({ quotes, onRemove }: WatchlistCardsProps) {
  const navigate = useNavigate();

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {quotes.map((item) => (
        <div
          key={item.code}
          className="rounded-xl border border-border bg-card p-4 cursor-pointer hover:shadow-md transition-shadow"
          onClick={() => navigate({ to: '/stock/$stockCode', params: { stockCode: item.code } })}
        >
          <div className="flex items-start justify-between mb-2">
            <div>
              <div className="flex items-center gap-2">
                <DataStatusBadge status={item.data_status} freshness={item.data_freshness} />
                <span className="font-semibold">{item.name || item.code}</span>
              </div>
              <div className="text-xs text-muted-foreground">{item.code}</div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={(e) => { e.stopPropagation(); onRemove(item.code); }}
            >
              移除
            </Button>
          </div>
          <div className="flex items-baseline gap-2 mb-2">
            <span className="text-xl font-bold">
              {item.latest_price != null ? formatNumber(item.latest_price) : '--'}
            </span>
            {item.change_pct != null && (
              <span className={`text-sm font-medium ${item.change_pct >= 0 ? 'text-red-500' : 'text-green-500'}`}>
                {formatPercent(item.change_pct)}
              </span>
            )}
          </div>
          {item.notes && (
            <p className="text-xs text-muted-foreground mb-2">{item.notes}</p>
          )}
          <div className="flex gap-3 text-xs text-muted-foreground">
            {item.pe != null && <span>PE {item.pe.toFixed(1)}</span>}
            {item.pb != null && <span>PB {item.pb.toFixed(1)}</span>}
            {item.dividend_yield != null && <span>股息 {formatPercent(item.dividend_yield)}</span>}
          </div>
        </div>
      ))}
    </div>
  );
}

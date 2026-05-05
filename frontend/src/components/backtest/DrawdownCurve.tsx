import { useEffect, useRef } from 'react';
import {
  AreaSeries,
  createChart,
  createSeriesMarkers,
  type IChartApi,
  type ISeriesApi,
  type LineData,
  type Time,
} from 'lightweight-charts';
import type { CurvePoint } from '@/types';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';

interface DrawdownCurveProps {
  drawdown: CurvePoint[];
  height?: number;
}

export function DrawdownCurve({ drawdown, height = 200 }: DrawdownCurveProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Area'> | null>(null);

  useEffect(() => {
    if (!containerRef.current || drawdown.length === 0) return;

    if (!chartRef.current) {
      const chart = createChart(containerRef.current, {
        height,
        layout: { background: { color: 'transparent' }, textColor: '#6b7280' },
        grid: {
          vertLines: { color: 'rgba(107, 114, 128, 0.1)' },
          horzLines: { color: 'rgba(107, 114, 128, 0.1)' },
        },
        rightPriceScale: {
          borderColor: 'rgba(107, 114, 128, 0.2)',
          scaleMargins: { top: 0.1, bottom: 0.1 },
        },
        timeScale: { borderColor: 'rgba(107, 114, 128, 0.2)', timeVisible: true },
      });
      chartRef.current = chart;
    }

    const chart = chartRef.current;

    if (seriesRef.current) {
      try { chart.removeSeries(seriesRef.current); } catch { /* ignore */ }
    }

    const minDD = Math.min(...drawdown.map((d) => d.value));
    const maxDDIdx = drawdown.findIndex((d) => d.value === minDD);

    const data: LineData[] = drawdown.map((p) => ({ time: p.date as Time, value: p.value }));
    const series = chart.addSeries(AreaSeries, {
      lineColor: '#ef4444',
      topColor: 'rgba(239, 68, 68, 0.15)',
      bottomColor: 'rgba(239, 68, 68, 0.01)',
      lineWidth: 2,
    });
    series.setData(data);
    seriesRef.current = series;

    if (maxDDIdx >= 0) {
      const marker = drawdown[maxDDIdx];
      createSeriesMarkers(series, [
        {
          time: marker.date as Time,
          position: 'belowBar',
          color: '#ef4444',
          shape: 'circle',
          text: `最大回撤 ${(minDD * 100).toFixed(1)}%`,
        },
      ]);
    }

    chart.timeScale().fitContent();

    return () => {};
  }, [drawdown, height]);

  useEffect(() => {
    return () => {
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
    };
  }, []);

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">回撤曲线</CardTitle>
      </CardHeader>
      <CardContent>
        <div ref={containerRef} />
      </CardContent>
    </Card>
  );
}

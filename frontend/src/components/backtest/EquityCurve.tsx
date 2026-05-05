import { useEffect, useRef } from 'react';
import { createChart, LineSeries, type IChartApi, type ISeriesApi, type LineData, type Time } from 'lightweight-charts';
import type { CurvePoint } from '@/types';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';

const COLORS = ['#ef4444', '#3b82f6', '#f59e0b', '#8b5cf6', '#06b6d4'];

interface EquityCurveProps {
  equity: CurvePoint[];
  benchmark?: CurvePoint[];
  comparisons?: { label: string; data: CurvePoint[] }[];
  height?: number;
}

export function EquityCurve({ equity, benchmark, comparisons, height = 400 }: EquityCurveProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRefs = useRef<ISeriesApi<'Line'>[]>([]);

  useEffect(() => {
    if (!containerRef.current || equity.length === 0) return;

    if (!chartRef.current) {
      const chart = createChart(containerRef.current, {
        height,
        layout: { background: { color: 'transparent' }, textColor: '#6b7280' },
        grid: {
          vertLines: { color: 'rgba(107, 114, 128, 0.1)' },
          horzLines: { color: 'rgba(107, 114, 128, 0.1)' },
        },
        rightPriceScale: { borderColor: 'rgba(107, 114, 128, 0.2)' },
        timeScale: { borderColor: 'rgba(107, 114, 128, 0.2)', timeVisible: true },
      });
      chartRef.current = chart;
    }

    const chart = chartRef.current;

    seriesRefs.current.forEach((s) => {
      try { chart.removeSeries(s); } catch { /* ignore */ }
    });
    seriesRefs.current = [];

    const eqData: LineData[] = equity.map((p) => ({ time: p.date as Time, value: p.value }));
    const eqSeries = chart.addSeries(LineSeries, { color: COLORS[0], lineWidth: 2 });
    eqSeries.setData(eqData);
    seriesRefs.current.push(eqSeries);

    if (benchmark && benchmark.length > 0) {
      const bmData: LineData[] = benchmark.map((p) => ({ time: p.date as Time, value: p.value }));
      const bmSeries = chart.addSeries(LineSeries, { color: '#9ca3af', lineWidth: 2, lineStyle: 2 });
      bmSeries.setData(bmData);
      seriesRefs.current.push(bmSeries);
    }

    if (comparisons) {
      comparisons.forEach((comp, i) => {
        const d: LineData[] = comp.data.map((p) => ({ time: p.date as Time, value: p.value }));
        const s = chart.addSeries(LineSeries, { color: COLORS[(i + 2) % COLORS.length], lineWidth: 2 });
        s.setData(d);
        seriesRefs.current.push(s);
      });
    }

    chart.timeScale().fitContent();

    return () => {};
  }, [equity, benchmark, comparisons, height]);

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
        <CardTitle className="text-sm">净值曲线</CardTitle>
      </CardHeader>
      <CardContent>
        <div ref={containerRef} />
        {(benchmark || comparisons) && (
          <div className="flex flex-wrap gap-4 mt-2 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <span className="w-3 h-0.5 inline-block" style={{ backgroundColor: COLORS[0] }} /> 策略
            </span>
            {benchmark && (
              <span className="flex items-center gap-1">
                <span className="w-3 h-0.5 inline-block border-t-2 border-dashed border-gray-400" /> 基准
              </span>
            )}
            {comparisons?.map((c, i) => (
              <span key={c.label} className="flex items-center gap-1">
                <span className="w-3 h-0.5 inline-block" style={{ backgroundColor: COLORS[(i + 2) % COLORS.length] }} />{' '}
                {c.label}
              </span>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

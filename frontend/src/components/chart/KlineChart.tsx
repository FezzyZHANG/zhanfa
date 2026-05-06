import { useEffect, useRef, useCallback } from 'react';
import {
  CandlestickSeries,
  createChart,
  HistogramSeries,
  LineSeries,
  type IChartApi,
  type ISeriesApi,
  type ITimeScaleApi,
  type IRange,
  type CandlestickData,
  type HistogramData,
  type LineData,
  type Time,
  type MouseEventParams,
} from 'lightweight-charts';
import type { KlineData, IndicatorConfig } from '@/types';
import type { ChartIndicatorResults } from '@/hooks/useChartData';

interface KlineChartProps {
  data: KlineData[];
  indicators: ChartIndicatorResults;
  indicatorConfigs: IndicatorConfig[];
  height?: number;
  comparisonData?: { code: string; name: string; data: KlineData[] }[];
  onCrosshairMove?: (data: KlineData | null, x: number, y: number) => void;
  onDateClick?: (date: string) => void;
  onTimeScaleReady?: (timeScale: SyncedTimeScale) => void;
  containerRef?: React.RefObject<HTMLDivElement | null>;
}

const COMPARISON_COLORS = ['#3b82f6', '#f59e0b', '#8b5cf6', '#06b6d4', '#ec4899'];

type VisibleTimeRange = IRange<Time> | null;

export interface SyncedTimeScale {
  subscribeVisibleTimeRangeChange: (handler: (range: unknown) => void) => () => void;
}

function createSyncedTimeScale(timeScale: ITimeScaleApi<Time>): SyncedTimeScale {
  return {
    subscribeVisibleTimeRangeChange: (handler) => {
      const timeRangeHandler = (range: VisibleTimeRange) => handler(range);
      timeScale.subscribeVisibleTimeRangeChange(timeRangeHandler);
      return () => timeScale.unsubscribeVisibleTimeRangeChange(timeRangeHandler);
    },
  };
}

export function KlineChart({
  data,
  indicators,
  indicatorConfigs,
  height = 400,
  comparisonData,
  onCrosshairMove,
  onDateClick,
  onTimeScaleReady,
  containerRef: externalRef,
}: KlineChartProps) {
  const internalRef = useRef<HTMLDivElement>(null);
  const ref = externalRef || internalRef;
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  const maSeriesRefs = useRef<ISeriesApi<'Line'>[]>([]);
  const bollSeriesRefs = useRef<ISeriesApi<'Line'>[]>([]);
  const donchianSeriesRefs = useRef<ISeriesApi<'Line'>[]>([]);
  const comparisonSeriesRefs = useRef<ISeriesApi<'Line'>[]>([]);

  const cleanupSeries = useCallback(() => {
    maSeriesRefs.current.forEach((s) => {
      try { chartRef.current?.removeSeries(s); } catch { /* ignore */ }
    });
    bollSeriesRefs.current.forEach((s) => {
      try { chartRef.current?.removeSeries(s); } catch { /* ignore */ }
    });
    donchianSeriesRefs.current.forEach((s) => {
      try { chartRef.current?.removeSeries(s); } catch { /* ignore */ }
    });
    comparisonSeriesRefs.current.forEach((s) => {
      try { chartRef.current?.removeSeries(s); } catch { /* ignore */ }
    });
    maSeriesRefs.current = [];
    bollSeriesRefs.current = [];
    donchianSeriesRefs.current = [];
    comparisonSeriesRefs.current = [];
  }, []);

  useEffect(() => {
    if (!ref.current || data.length === 0) return;

    // Create chart if needed
    if (!chartRef.current) {
      const chart = createChart(ref.current, {
        height,
        layout: {
          background: { color: 'transparent' },
          textColor: '#6b7280',
        },
        grid: {
          vertLines: { color: 'rgba(107, 114, 128, 0.1)' },
          horzLines: { color: 'rgba(107, 114, 128, 0.1)' },
        },
        crosshair: {
          mode: 1,
          vertLine: {
            color: 'rgba(107, 114, 128, 0.3)',
            width: 1,
            style: 2,
          },
          horzLine: {
            color: 'rgba(107, 114, 128, 0.3)',
            width: 1,
            style: 2,
          },
        },
        rightPriceScale: {
          borderColor: 'rgba(107, 114, 128, 0.2)',
        },
        timeScale: {
          borderColor: 'rgba(107, 114, 128, 0.2)',
          timeVisible: true,
        },
      });

      // Candlestick series
      const candleSeries = chart.addSeries(CandlestickSeries, {
        upColor: '#ef4444',
        downColor: '#22c55e',
        borderUpColor: '#ef4444',
        borderDownColor: '#22c55e',
        wickUpColor: '#ef4444',
        wickDownColor: '#22c55e',
      });

      // Volume series
      const volumeSeries = chart.addSeries(HistogramSeries, {
        priceFormat: { type: 'volume' },
        priceScaleId: 'volume',
      });
      volumeSeries.priceScale().applyOptions({
        scaleMargins: { top: 0.8, bottom: 0 },
      });

      chartRef.current = chart;
      candleSeriesRef.current = candleSeries;
      volumeSeriesRef.current = volumeSeries;

      // Crosshair
      chart.subscribeCrosshairMove((param: MouseEventParams) => {
        if (!onCrosshairMove) return;
        if (!param.time || param.point === undefined) {
          onCrosshairMove(null, 0, 0);
          return;
        }
        const timeStr = param.time as string;
        const item = data.find((d) => d.date === timeStr);
        onCrosshairMove(item || null, param.point.x, param.point.y);
      });

      // Click
      if (onDateClick) {
        chart.subscribeClick((param: MouseEventParams) => {
          if (param.time) onDateClick(param.time as string);
        });
      }

      // Expose time scale
      if (onTimeScaleReady) {
        onTimeScaleReady(createSyncedTimeScale(chart.timeScale()));
      }
    }

    const chart = chartRef.current;
    const candleSeries = candleSeriesRef.current;
    const volumeSeries = volumeSeriesRef.current;
    if (!chart || !candleSeries || !volumeSeries) return;

    // Update candlestick data
    const candleData: CandlestickData[] = data.map((d) => ({
      time: d.date as Time,
      open: d.open,
      high: d.high,
      low: d.low,
      close: d.close,
    }));
    candleSeries.setData(candleData);

    // Update volume data
    const volumeData: HistogramData[] = data.map((d) => ({
      time: d.date as Time,
      value: d.volume,
      color: d.close >= d.open ? 'rgba(239, 68, 68, 0.3)' : 'rgba(34, 197, 94, 0.3)',
    }));
    volumeSeries.setData(volumeData);

    // Clean up old indicator series
    cleanupSeries();

    // MA lines
    const maConfigs = indicatorConfigs.filter((c) => c.type === 'MA' && c.visible);
    const hasMA = maConfigs.length > 0;

    if (hasMA) {
      const maSources = [
        { key: 'sma5' as const, period: 5, color: '#f59e0b', label: 'MA5' },
        { key: 'sma10' as const, period: 10, color: '#3b82f6', label: 'MA10' },
        { key: 'sma20' as const, period: 20, color: '#8b5cf6', label: 'MA20' },
        { key: 'sma60' as const, period: 60, color: '#06b6d4', label: 'MA60' },
      ];

      for (const src of maSources) {
        const smaResult = indicators[src.key];
        if (!smaResult) continue;
        const lineData: LineData[] = [];
        for (let i = 0; i < data.length; i++) {
          if (smaResult.values[i] != null) {
            lineData.push({ time: data[i].date as Time, value: smaResult.values[i]! });
          }
        }
        if (lineData.length > 0) {
          const series = chart.addSeries(LineSeries, {
            color: src.color,
            lineWidth: 1,
          });
          series.setData(lineData);
          maSeriesRefs.current.push(series);
        }
      }
    }

    // EMA12
    const ema12Config = indicatorConfigs.find((c) => c.type === 'MA' && c.visible);
    if (ema12Config && indicators.ema12) {
      const lineData: LineData[] = [];
      for (let i = 0; i < data.length; i++) {
        if (indicators.ema12.values[i] != null) {
          lineData.push({ time: data[i].date as Time, value: indicators.ema12.values[i]! });
        }
      }
      if (lineData.length > 0) {
        const series = chart.addSeries(LineSeries, { color: '#ec4899', lineWidth: 1, lineStyle: 2 });
        series.setData(lineData);
        maSeriesRefs.current.push(series);
      }
    }

    // EMA26
    if (ema12Config && indicators.ema26) {
      const lineData: LineData[] = [];
      for (let i = 0; i < data.length; i++) {
        if (indicators.ema26.values[i] != null) {
          lineData.push({ time: data[i].date as Time, value: indicators.ema26.values[i]! });
        }
      }
      if (lineData.length > 0) {
        const series = chart.addSeries(LineSeries, { color: '#f97316', lineWidth: 1, lineStyle: 2 });
        series.setData(lineData);
        maSeriesRefs.current.push(series);
      }
    }

    // Bollinger Bands
    const bollConfig = indicatorConfigs.find((c) => c.type === 'BOLL' && c.visible);
    if (bollConfig && indicators.boll) {
      const boll = indicators.boll;
      const bollColors = ['rgba(168, 85, 247, 0.6)', 'rgba(168, 85, 247, 0.8)', 'rgba(168, 85, 247, 0.6)'];
      const keys: ('upper' | 'middle' | 'lower')[] = ['upper', 'middle', 'lower'];

      for (let k = 0; k < 3; k++) {
        const lineData: LineData[] = [];
        for (let i = 0; i < data.length; i++) {
          if (boll[keys[k]][i] != null) {
            lineData.push({ time: data[i].date as Time, value: boll[keys[k]][i]! });
          }
        }
        if (lineData.length > 0) {
          const series = chart.addSeries(LineSeries, {
            color: bollColors[k],
            lineWidth: 1,
            lineStyle: k === 1 ? 0 : 2,
          });
          series.setData(lineData);
          bollSeriesRefs.current.push(series);
        }
      }
    }

    // Donchian Channel
    const donchianConfig = indicatorConfigs.find((c) => c.type === 'DONCHIAN' && c.visible);
    if (donchianConfig && indicators.donchian) {
      const dc = indicators.donchian;
      const dcColors = ['rgba(14, 165, 233, 0.5)', 'rgba(14, 165, 233, 0.3)'];

      for (let k = 0; k < 2; k++) {
        const key: 'upper' | 'lower' = k === 0 ? 'upper' : 'lower';
        const lineData: LineData[] = [];
        for (let i = 0; i < data.length; i++) {
          if (dc[key][i] != null) {
            lineData.push({ time: data[i].date as Time, value: dc[key][i]! });
          }
        }
        if (lineData.length > 0) {
          const series = chart.addSeries(LineSeries, {
            color: dcColors[k],
            lineWidth: 1,
          });
          series.setData(lineData);
          donchianSeriesRefs.current.push(series);
        }
      }
    }

    // Comparison stocks
    if (comparisonData && comparisonData.length > 0) {
      const baseClose = data[0]?.close || 1;

      for (let ci = 0; ci < comparisonData.length; ci++) {
        const comp = comparisonData[ci];
        if (!comp.data || comp.data.length === 0) continue;

        // Align by date — create a map
        const compMap = new Map(comp.data.map((d) => [d.date, d.close]));
        const compBase = comp.data[0]?.close || 1;

        const lineData: LineData[] = [];
        for (const d of data) {
          const compClose = compMap.get(d.date);
          if (compClose !== undefined) {
            // Normalize to base stock's price level for visual comparison
            const normalized = (compClose / compBase) * baseClose;
            lineData.push({ time: d.date as Time, value: normalized });
          }
        }

        if (lineData.length > 0) {
          const series = chart.addSeries(LineSeries, {
            color: COMPARISON_COLORS[ci % COMPARISON_COLORS.length],
            lineWidth: 2,
          });
          series.setData(lineData);
          comparisonSeriesRefs.current.push(series);
        }
      }
    }

    chart.timeScale().fitContent();

    return () => {
      // Don't remove chart on data change, just on unmount
    };
  }, [data, indicators, indicatorConfigs, comparisonData, height, onCrosshairMove, onDateClick, onTimeScaleReady, cleanupSeries, ref]);

  // Chart instance cleanup on unmount
  useEffect(() => {
    return () => {
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
        candleSeriesRef.current = null;
        volumeSeriesRef.current = null;
      }
    };
  }, []);

  return <div ref={ref} />;
}

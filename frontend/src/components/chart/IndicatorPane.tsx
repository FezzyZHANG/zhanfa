import { useEffect, useRef } from 'react';
import {
  createChart,
  HistogramSeries,
  LineSeries,
  type IChartApi,
  type IRange,
  type LineData,
  type HistogramData,
  type Time,
} from 'lightweight-charts';
import type { MACDResult, RSIResult, BollResult, DonchianResult } from '@/lib/indicators';
import type { SyncedTimeScale } from './KlineChart';

type PaneType = 'MACD' | 'RSI' | 'BOLL' | 'DONCHIAN';

function isVisibleTimeRange(range: unknown): range is IRange<Time> {
  return (
    typeof range === 'object' &&
    range !== null &&
    'from' in range &&
    'to' in range
  );
}

interface IndicatorPaneProps {
  type: PaneType;
  data: { time: string }[];
  macd?: MACDResult;
  rsi?: RSIResult;
  boll?: BollResult;
  donchian?: DonchianResult;
  height?: number;
  mainTimeScale?: SyncedTimeScale;
}

export function IndicatorPane({
  type,
  data,
  macd,
  rsi,
  boll,
  donchian,
  height = 150,
  mainTimeScale,
}: IndicatorPaneProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!containerRef.current || data.length === 0) return;

    const chart = createChart(containerRef.current, {
      height,
      layout: {
        background: { color: 'transparent' },
        textColor: '#6b7280',
      },
      grid: {
        vertLines: { color: 'rgba(107, 114, 128, 0.1)' },
        horzLines: { color: 'rgba(107, 114, 128, 0.1)' },
      },
      crosshair: { mode: 0 },
      rightPriceScale: {
        borderColor: 'rgba(107, 114, 128, 0.2)',
        scaleMargins: { top: 0.05, bottom: 0.05 },
      },
      timeScale: {
        borderColor: 'rgba(107, 114, 128, 0.2)',
        visible: false,
      },
    });

    chartRef.current = chart;

    if (type === 'MACD' && macd) {
      const difSeries = chart.addSeries(LineSeries, {
        color: '#3b82f6',
        lineWidth: 1,
      });
      const deaSeries = chart.addSeries(LineSeries, {
        color: '#f59e0b',
        lineWidth: 1,
      });
      const histogramSeries = chart.addSeries(HistogramSeries, {
        color: 'rgba(239, 68, 68, 0.5)',
      });

      const difData: LineData[] = [];
      const deaData: LineData[] = [];
      const histData: HistogramData[] = [];

      for (let i = 0; i < data.length; i++) {
        const t = data[i].time as Time;
        if (macd.dif[i] != null) difData.push({ time: t, value: macd.dif[i]! });
        if (macd.dea[i] != null) deaData.push({ time: t, value: macd.dea[i]! });
        if (macd.histogram[i] != null) {
          histData.push({
            time: t,
            value: macd.histogram[i]!,
            color: macd.histogram[i]! >= 0 ? 'rgba(239, 68, 68, 0.5)' : 'rgba(34, 197, 94, 0.5)',
          });
        }
      }

      difSeries.setData(difData);
      deaSeries.setData(deaData);
      histogramSeries.setData(histData);
    }

    if (type === 'RSI' && rsi) {
      const rsiSeries = chart.addSeries(LineSeries, {
        color: '#8b5cf6',
        lineWidth: 2,
      });

      // Add reference lines at 70 and 30
      const overboughtLine = chart.addSeries(LineSeries, {
        color: 'rgba(239, 68, 68, 0.3)',
        lineWidth: 1,
        lineStyle: 2,
      });
      const oversoldLine = chart.addSeries(LineSeries, {
        color: 'rgba(34, 197, 94, 0.3)',
        lineWidth: 1,
        lineStyle: 2,
      });

      const rsiData: LineData[] = [];
      const refData: LineData[] = [];

      for (let i = 0; i < data.length; i++) {
        const t = data[i].time as Time;
        if (rsi.values[i] != null) {
          rsiData.push({ time: t, value: rsi.values[i]! });
          refData.push({ time: t, value: 70 });
          refData.push({ time: t, value: 30 });
        }
      }

      rsiSeries.setData(rsiData);

      if (refData.length > 0) {
        overboughtLine.setData(refData.filter((_, i) => i % 2 === 0));
        oversoldLine.setData(refData.filter((_, i) => i % 2 === 1));
      }
    }

    // Sync time scale with main chart
    if (mainTimeScale) {
      const handler = (range: unknown) => {
        if (isVisibleTimeRange(range)) {
          chart.timeScale().setVisibleRange(range);
        }
      };
      const unsubscribe = mainTimeScale.subscribeVisibleTimeRangeChange(handler);
      return () => {
        unsubscribe();
        chart.remove();
      };
    }

    chart.timeScale().fitContent();

    return () => {
      chart.remove();
    };
  }, [type, data, macd, rsi, boll, donchian, height, mainTimeScale]);

  return <div ref={containerRef} />;
}

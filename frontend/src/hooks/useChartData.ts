import { useMemo } from 'react';
import { useKline } from './useStocks';
import type { KlineData, Freq } from '@/types';
import { isMinuteFreq } from '@/types';
import {
  calcSMA,
  calcEMA,
  calcMACD,
  calcRSI,
  calcBollinger,
  calcDonchian,
} from '@/lib/indicators';
import type { SMAResult, MAResult, MACDResult, RSIResult, BollResult, DonchianResult } from '@/lib/indicators';

function aggregateData(data: KlineData[], freq: Freq): KlineData[] {
  // 分钟级数据直接从服务端获取，无需客户端聚合
  if (freq === 'D' || isMinuteFreq(freq) || data.length === 0) return data;

  const grouped = new Map<string, KlineData[]>();

  for (const d of data) {
    let key: string;
    const dt = new Date(d.date);
    switch (freq) {
      case 'W': {
        const startOfYear = new Date(dt.getFullYear(), 0, 1);
        const weekNum = Math.ceil(
          ((dt.getTime() - startOfYear.getTime()) / 86400000 + startOfYear.getDay() + 1) / 7,
        );
        key = `${dt.getFullYear()}-W${String(weekNum).padStart(2, '0')}`;
        break;
      }
      case 'M':
        key = `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, '0')}`;
        break;
      case 'Q':
        key = `${dt.getFullYear()}-Q${Math.ceil((dt.getMonth() + 1) / 3)}`;
        break;
      case 'Y':
        key = `${dt.getFullYear()}`;
        break;
      default:
        key = d.date;
        break;
    }
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key)!.push(d);
  }

  return Array.from(grouped.entries()).map(([, items]) => {
    const first = items[0];
    const last = items[items.length - 1];
    return {
      date: first.date,
      open: first.open,
      high: Math.max(...items.map((d) => d.high)),
      low: Math.min(...items.map((d) => d.low)),
      close: last.close,
      volume: items.reduce((s, d) => s + d.volume, 0),
    };
  });
}

export interface ChartIndicatorResults {
  sma5: SMAResult;
  sma10: SMAResult;
  sma20: SMAResult;
  sma60: SMAResult;
  ema12: MAResult;
  ema26: MAResult;
  macd: MACDResult;
  rsi: RSIResult;
  boll: BollResult;
  donchian: DonchianResult;
}

export interface ChartDataResult {
  data: KlineData[];
  indicators: ChartIndicatorResults | null;
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
}

export function useChartData(
  code: string,
  freq: Freq = 'D',
  start?: string,
  end?: string,
): ChartDataResult {
  const apiFreq = isMinuteFreq(freq) ? freq : 'daily';
  const { data: raw, isLoading, isError, error } = useKline(code, start, end, apiFreq);

  const result = useMemo(() => {
    if (!raw || raw.length === 0) {
      return { data: [] as KlineData[], indicators: null };
    }

    const sorted = [...raw].sort((a, b) => a.date.localeCompare(b.date));
    const data = aggregateData(sorted, freq);

    return {
      data,
      indicators: {
        sma5: calcSMA(data, 5),
        sma10: calcSMA(data, 10),
        sma20: calcSMA(data, 20),
        sma60: calcSMA(data, 60),
        ema12: calcEMA(data, 12),
        ema26: calcEMA(data, 26),
        macd: calcMACD(data),
        rsi: calcRSI(data),
        boll: calcBollinger(data),
        donchian: calcDonchian(data),
      },
    };
  }, [raw, freq]);

  return { ...result, isLoading, isError, error: error as Error | null };
}

import { describe, expect, it } from 'vitest';
import { aggregateData } from './useChartData';
import type { KlineData } from '@/types';

const daily: KlineData[] = [
  { date: '2024-01-02', open: 10, high: 12, low: 9, close: 11, volume: 100 },
  { date: '2024-01-03', open: 11, high: 13, low: 10, close: 12, volume: 200 },
  { date: '2024-02-01', open: 12, high: 14, low: 11, close: 13, volume: 300 },
  { date: '2024-04-01', open: 13, high: 15, low: 12, close: 14, volume: 400 },
  { date: '2025-01-02', open: 14, high: 16, low: 13, close: 15, volume: 500 },
];

describe('aggregateData', () => {
  it('returns daily and minute data unchanged', () => {
    expect(aggregateData(daily, 'D')).toBe(daily);
    expect(aggregateData(daily, '60min')).toBe(daily);
  });

  it('aggregates monthly OHLCV', () => {
    const result = aggregateData(daily, 'M');

    expect(result[0]).toEqual({
      date: '2024-01-02',
      open: 10,
      high: 13,
      low: 9,
      close: 12,
      volume: 300,
    });
  });

  it('aggregates weekly, quarterly and yearly groups', () => {
    expect(aggregateData(daily, 'W')[0]).toEqual({
      date: '2024-01-02',
      open: 10,
      high: 13,
      low: 9,
      close: 12,
      volume: 300,
    });
    expect(aggregateData(daily, 'Q')).toHaveLength(3);
    expect(aggregateData(daily, 'Y')).toEqual([
      { date: '2024-01-02', open: 10, high: 15, low: 9, close: 14, volume: 1000 },
      { date: '2025-01-02', open: 14, high: 16, low: 13, close: 15, volume: 500 },
    ]);
  });
});

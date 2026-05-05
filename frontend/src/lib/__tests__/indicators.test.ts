import { describe, it, expect } from 'vitest';
import {
  calcSMA,
  calcEMA,
  calcMACD,
  calcRSI,
  calcBollinger,
  calcDonchian,
} from '@/lib/indicators';
import type { KlineData } from '@/types';

function makeData(closes: number[]): KlineData[] {
  return closes.map((close, i) => ({
    date: `2024-01-${String(i + 1).padStart(2, '0')}`,
    open: close,
    high: close + 1,
    low: close - 1,
    close,
    volume: 10000,
  }));
}

describe('calcSMA', () => {
  it('computes simple moving average', () => {
    const data = makeData([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
    const result = calcSMA(data, 3);
    expect(result.values[0]).toBeNull();
    expect(result.values[1]).toBeNull();
    expect(result.values[2]).toBeCloseTo(2); // (1+2+3)/3
    expect(result.values[3]).toBeCloseTo(3); // (2+3+4)/3
    expect(result.values[9]).toBeCloseTo(9); // (8+9+10)/3
  });

  it('returns period in result', () => {
    const data = makeData([1, 2, 3, 4, 5]);
    expect(calcSMA(data, 5).period).toBe(5);
  });

  it('returns all nulls when data shorter than period', () => {
    const data = makeData([1, 2]);
    const result = calcSMA(data, 5);
    expect(result.values.every((v) => v === null)).toBe(true);
  });
});

describe('calcEMA', () => {
  it('computes exponential moving average', () => {
    const data = makeData([10, 10, 10, 10, 10]);
    const result = calcEMA(data, 3);
    // First 2 are null, then SMA for seed, then EMA stays constant
    expect(result.values[0]).toBeNull();
    expect(result.values[1]).toBeNull();
    expect(result.values[2]).toBeCloseTo(10); // seed SMA
    expect(result.values[3]).toBeCloseTo(10);
    expect(result.values[4]).toBeCloseTo(10);
  });

  it('has type EMA', () => {
    const data = makeData([1, 2, 3, 4, 5]);
    expect(calcEMA(data, 3).type).toBe('EMA');
  });

  it('returns nulls before enough data', () => {
    const data = makeData([1, 2, 3, 4]);
    const result = calcEMA(data, 5);
    expect(result.values.every((v) => v === null)).toBe(true);
  });
});

describe('calcMACD', () => {
  it('computes MACD with default params', () => {
    // 40 data points all at same price → dif/dea/histogram should be ~0
    const data = makeData(Array(40).fill(100));
    const result = calcMACD(data);
    expect(result.params).toEqual({ fast: 12, slow: 26, signal: 9 });
    // At the end, all should be near zero
    const last = result.dif.length - 1;
    expect(Math.abs(result.dif[last]!)).toBeLessThan(0.01);
    expect(Math.abs(result.dea[last]!)).toBeLessThan(0.01);
    expect(Math.abs(result.histogram[last]!)).toBeLessThan(0.01);
  });

  it('produces nulls before enough data', () => {
    const data = makeData(Array(10).fill(100));
    const result = calcMACD(data);
    // With slow=26, all values should be null for < 26 points
    expect(result.dif.every((v) => v === null)).toBe(true);
  });

  it('accepts custom params', () => {
    const data = makeData(Array(30).fill(100));
    const result = calcMACD(data, 5, 10, 5);
    expect(result.params).toEqual({ fast: 5, slow: 10, signal: 5 });
  });
});

describe('calcRSI', () => {
  it('computes RSI with default period 14', () => {
    // All same price → no gains/losses → RSI = 100 (avgLoss = 0)
    const data = makeData(Array(20).fill(100));
    const result = calcRSI(data);
    expect(result.period).toBe(14);
    expect(result.values[0]).toBeNull(); // first has no prev
    // With constant price, avgLoss = 0, so RSI = 100
    const last = result.values[result.values.length - 1];
    expect(last).toBe(100);
  });

  it('produces nulls for first <period> values', () => {
    const data = makeData(Array(20).fill(100));
    const result = calcRSI(data, 14);
    // First is always null (no delta), next 13 are null (warm-up)
    for (let i = 0; i < 15; i++) {
      if (i === 0) expect(result.values[i]).toBeNull();
    }
  });

  it('produces values between 0 and 100', () => {
    const closes = Array.from({ length: 50 }, (_, i) => 100 + Math.sin(i * 0.5) * 10);
    const data = makeData(closes);
    const result = calcRSI(data, 14);
    for (const v of result.values) {
      if (v !== null) {
        expect(v).toBeGreaterThanOrEqual(0);
        expect(v).toBeLessThanOrEqual(100);
      }
    }
  });
});

describe('calcBollinger', () => {
  it('computes Bollinger Bands', () => {
    // Constant price → std = 0, bands converge to MA
    const data = makeData(Array(25).fill(100));
    const result = calcBollinger(data, 20, 2);
    expect(result.params).toEqual({ period: 20, multiplier: 2 });
    expect(result.upper[24]).toBeCloseTo(100);
    expect(result.middle[24]).toBeCloseTo(100);
    expect(result.lower[24]).toBeCloseTo(100);
  });

  it('returns nulls before enough data', () => {
    const data = makeData(Array(10).fill(100));
    const result = calcBollinger(data, 20, 2);
    expect(result.upper.every((v) => v === null)).toBe(true);
  });

  it('upper > middle > lower with varying prices', () => {
    const closes = Array.from({ length: 30 }, (_, i) => 100 + i);
    const data = makeData(closes);
    const result = calcBollinger(data, 20, 2);
    const last = data.length - 1;
    expect(result.upper[last]!).toBeGreaterThan(result.middle[last]!);
    expect(result.middle[last]!).toBeGreaterThan(result.lower[last]!);
  });
});

describe('calcDonchian', () => {
  it('computes Donchian Channel', () => {
    const data = makeData(Array(25).fill(100));
    const result = calcDonchian(data, 20);
    expect(result.period).toBe(20);
    // upper = max high, lower = min low, middle = avg
    expect(result.upper[24]).toBeCloseTo(101); // high = close + 1
    expect(result.lower[24]).toBeCloseTo(99); // low = close - 1
    expect(result.middle[24]).toBeCloseTo(100);
  });

  it('returns nulls before enough data', () => {
    const data = makeData(Array(10).fill(100));
    const result = calcDonchian(data, 20);
    expect(result.upper.every((v) => v === null)).toBe(true);
  });
});

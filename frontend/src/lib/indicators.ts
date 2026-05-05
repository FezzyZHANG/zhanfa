import type { KlineData } from '@/types';

export interface SMAResult {
  values: (number | null)[];
  period: number;
}

export function calcSMA(data: KlineData[], period: number): SMAResult {
  const values: (number | null)[] = [];
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) {
      values.push(null);
    } else {
      let sum = 0;
      for (let j = i - period + 1; j <= i; j++) sum += data[j].close;
      values.push(sum / period);
    }
  }
  return { values, period };
}

export interface MAResult {
  values: (number | null)[];
  period: number;
  type: 'SMA' | 'EMA';
}

export function calcEMA(data: KlineData[], period: number): MAResult {
  const values: (number | null)[] = [];
  const k = 2 / (period + 1);
  let prev: number | null = null;
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) {
      values.push(null);
    } else if (i === period - 1 || prev === null) {
      let sum = 0;
      for (let j = i - period + 1; j <= i; j++) sum += data[j].close;
      prev = sum / period;
      values.push(prev);
    } else {
      prev = data[i].close * k + prev * (1 - k);
      values.push(prev);
    }
  }
  return { values, period, type: 'EMA' };
}

export interface MACDResult {
  dif: (number | null)[];
  dea: (number | null)[];
  histogram: (number | null)[];
  params: { fast: number; slow: number; signal: number };
}

export function calcMACD(
  data: KlineData[],
  fast = 12,
  slow = 26,
  signal = 9,
): MACDResult {
  const emaFast = calcEMAValues(data, fast);
  const emaSlow = calcEMAValues(data, slow);

  const dif: (number | null)[] = [];
  for (let i = 0; i < data.length; i++) {
    if (emaFast[i] == null || emaSlow[i] == null) {
      dif.push(null);
    } else {
      dif.push(emaFast[i]! - emaSlow[i]!);
    }
  }

  const dea = calcEMAFromValues(dif, signal);
  const histogram: (number | null)[] = [];
  for (let i = 0; i < data.length; i++) {
    if (dif[i] == null || dea[i] == null) {
      histogram.push(null);
    } else {
      histogram.push((dif[i]! - dea[i]!) * 2);
    }
  }

  return { dif, dea, histogram, params: { fast, slow, signal } };
}

function calcEMAValues(data: KlineData[], period: number): (number | null)[] {
  const values: (number | null)[] = [];
  const k = 2 / (period + 1);
  let prev: number | null = null;
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) {
      values.push(null);
    } else if (i === period - 1 || prev === null) {
      let sum = 0;
      for (let j = i - period + 1; j <= i; j++) sum += data[j].close;
      prev = sum / period;
      values.push(prev);
    } else {
      prev = data[i].close * k + prev * (1 - k);
      values.push(prev);
    }
  }
  return values;
}

function calcEMAFromValues(input: (number | null)[], period: number): (number | null)[] {
  const values: (number | null)[] = [];
  const k = 2 / (period + 1);
  let prev: number | null = null;
  let firstIdx = -1;
  for (let i = 0; i < input.length; i++) {
    if (input[i] == null) {
      values.push(null);
      continue;
    }
    if (firstIdx < 0) firstIdx = i;
    if (i - firstIdx < period - 1) {
      values.push(null);
    } else if (prev === null) {
      let sum = 0;
      let count = 0;
      for (let j = firstIdx; j <= i; j++) {
        if (input[j] != null) {
          sum += input[j]!;
          count++;
        }
      }
      prev = count > 0 ? sum / count : 0;
      values.push(prev);
    } else {
      prev = input[i]! * k + prev * (1 - k);
      values.push(prev);
    }
  }
  return values;
}

export interface RSIResult {
  values: (number | null)[];
  period: number;
}

export function calcRSI(data: KlineData[], period = 14): RSIResult {
  const values: (number | null)[] = [];
  let avgGain = 0;
  let avgLoss = 0;

  for (let i = 1; i < data.length; i++) {
    const delta = data[i].close - data[i - 1].close;
    const gain = delta > 0 ? delta : 0;
    const loss = delta < 0 ? -delta : 0;

    if (i < period) {
      avgGain += gain;
      avgLoss += loss;
      if (i < period - 1) {
        values.push(null);
        continue;
      }
      avgGain /= period;
      avgLoss /= period;
    } else {
      avgGain = (avgGain * (period - 1) + gain) / period;
      avgLoss = (avgLoss * (period - 1) + loss) / period;
    }

    if (avgLoss === 0) {
      values.push(100);
    } else {
      values.push(100 - 100 / (1 + avgGain / avgLoss));
    }
  }
  // First data point has no previous close for delta
  values.unshift(null);

  return { values, period };
}

export interface BollResult {
  upper: (number | null)[];
  middle: (number | null)[];
  lower: (number | null)[];
  params: { period: number; multiplier: number };
}

export function calcBollinger(
  data: KlineData[],
  period = 20,
  multiplier = 2,
): BollResult {
  const upper: (number | null)[] = [];
  const middle: (number | null)[] = [];
  const lower: (number | null)[] = [];

  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) {
      upper.push(null);
      middle.push(null);
      lower.push(null);
      continue;
    }
    let sum = 0;
    for (let j = i - period + 1; j <= i; j++) sum += data[j].close;
    const ma = sum / period;

    let variance = 0;
    for (let j = i - period + 1; j <= i; j++) {
      variance += (data[j].close - ma) ** 2;
    }
    const std = Math.sqrt(variance / period);

    upper.push(ma + multiplier * std);
    middle.push(ma);
    lower.push(ma - multiplier * std);
  }

  return { upper, middle, lower, params: { period, multiplier } };
}

export interface DonchianResult {
  upper: (number | null)[];
  middle: (number | null)[];
  lower: (number | null)[];
  period: number;
}

export function calcDonchian(data: KlineData[], period = 20): DonchianResult {
  const upper: (number | null)[] = [];
  const middle: (number | null)[] = [];
  const lower: (number | null)[] = [];

  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) {
      upper.push(null);
      middle.push(null);
      lower.push(null);
      continue;
    }
    let maxH = -Infinity;
    let minL = Infinity;
    for (let j = i - period + 1; j <= i; j++) {
      if (data[j].high > maxH) maxH = data[j].high;
      if (data[j].low < minL) minL = data[j].low;
    }
    upper.push(maxH);
    middle.push((maxH + minL) / 2);
    lower.push(minL);
  }

  return { upper, middle, lower, period };
}

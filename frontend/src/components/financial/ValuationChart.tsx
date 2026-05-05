import ReactEChartsCore from 'echarts-for-react';
import type { FinancialData } from '@/types';

interface ValuationChartProps {
  data: FinancialData[];
  height?: number;
}

export function ValuationChart({ data, height = 300 }: ValuationChartProps) {
  const sorted = [...data].sort((a, b) => a.report_date.localeCompare(b.report_date));

  const peValues = sorted.map((d) => d.pe);
  const pbValues = sorted.map((d) => d.pb);
  const currentPE = peValues[peValues.length - 1];
  const currentPB = pbValues[pbValues.length - 1];
  const peMin = Math.min(...peValues);
  const peMax = Math.max(...peValues);
  const pbMin = Math.min(...pbValues);
  const pbMax = Math.max(...pbValues);
  const pePercentile = peMax > peMin ? ((currentPE - peMin) / (peMax - peMin)) * 100 : 50;
  const pbPercentile = pbMax > pbMin ? ((currentPB - pbMin) / (pbMax - pbMin)) * 100 : 50;

  function percentileColor(pct: number) {
    if (pct < 25) return '#22c55e';
    if (pct < 50) return '#84cc16';
    if (pct < 75) return '#f59e0b';
    return '#ef4444';
  }

  const option = {
    tooltip: {
      trigger: 'axis' as const,
      formatter: (params: Record<string, unknown>[]) => {
        const p0 = params[0] as { axisValue: string; value: number };
        const p1 = params[1] as { value: number };
        return `${p0.axisValue}<br/>PE: ${p0.value.toFixed(1)}<br/>PB: ${p1.value.toFixed(2)}`;
      },
    },
    legend: { data: ['PE', 'PB'], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '12%', top: '8%', containLabel: true },
    xAxis: {
      type: 'category' as const,
      data: sorted.map((d) => d.report_date),
      axisLabel: { rotate: 30 },
    },
    yAxis: [
      {
        type: 'value' as const,
        name: 'PE',
      },
      {
        type: 'value' as const,
        name: 'PB',
      },
    ],
    series: [
      {
        name: 'PE',
        type: 'line',
        data: peValues,
        itemStyle: { color: '#3b82f6' },
        lineStyle: { width: 2 },
        symbol: 'circle',
        symbolSize: 6,
        markLine: {
          silent: true,
          data: [
            { yAxis: peMin, name: `最低 ${peMin.toFixed(1)}`, label: { formatter: '最低 {c}' } },
            { yAxis: peMax, name: `最高 ${peMax.toFixed(1)}`, label: { formatter: '最高 {c}' } },
          ],
          lineStyle: { color: '#94a3b8', type: 'dashed' as const },
        },
      },
      {
        name: 'PB',
        type: 'line',
        yAxisIndex: 1,
        data: pbValues,
        itemStyle: { color: '#a855f7' },
        lineStyle: { width: 2 },
        symbol: 'diamond',
        symbolSize: 6,
        markLine: {
          silent: true,
          data: [
            { yAxis: pbMin, name: `最低 ${pbMin.toFixed(2)}`, label: { formatter: '最低 {c}' } },
            { yAxis: pbMax, name: `最高 ${pbMax.toFixed(2)}`, label: { formatter: '最高 {c}' } },
          ],
          lineStyle: { color: '#94a3b8', type: 'dashed' as const },
        },
      },
    ],
  };

  return (
    <div>
      <ReactEChartsCore option={option} style={{ height }} notMerge />
      <div className="flex justify-center gap-8 mt-2 text-sm">
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground">PE 当前分位:</span>
          <span className="font-bold" style={{ color: percentileColor(pePercentile) }}>
            {pePercentile.toFixed(0)}%
          </span>
          <span className="text-muted-foreground">
            ({currentPE.toFixed(1)} / {peMin.toFixed(1)}–{peMax.toFixed(1)})
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground">PB 当前分位:</span>
          <span className="font-bold" style={{ color: percentileColor(pbPercentile) }}>
            {pbPercentile.toFixed(0)}%
          </span>
          <span className="text-muted-foreground">
            ({currentPB.toFixed(2)} / {pbMin.toFixed(2)}–{pbMax.toFixed(2)})
          </span>
        </div>
      </div>
    </div>
  );
}

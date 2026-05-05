import ReactEChartsCore from 'echarts-for-react';
import type { FinancialData } from '@/types';

interface MarginChartProps {
  data: FinancialData[];
  height?: number;
}

export function MarginChart({ data, height = 300 }: MarginChartProps) {
  const sorted = [...data].sort((a, b) => a.report_date.localeCompare(b.report_date));

  const option = {
    tooltip: {
      trigger: 'axis' as const,
      formatter: (params: Record<string, unknown>[]) => {
        const p0 = params[0] as { axisValue: string; value: number };
        const p1 = params[1] as { value: number };
        return `${p0.axisValue}<br/>毛利率: ${p0.value}%<br/>净利率: ${p1.value}%`;
      },
    },
    legend: { data: ['毛利率', '净利率'], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '12%', top: '8%', containLabel: true },
    xAxis: {
      type: 'category' as const,
      data: sorted.map((d) => d.report_date),
      axisLabel: { rotate: 30 },
    },
    yAxis: {
      type: 'value' as const,
      name: '%',
      axisLabel: { formatter: '{value}%' },
    },
    series: [
      {
        name: '毛利率',
        type: 'line',
        data: sorted.map((d) => +(d.gross_margin * 100).toFixed(1)),
        itemStyle: { color: '#8b5cf6' },
        lineStyle: { width: 2 },
        symbol: 'circle',
        symbolSize: 6,
      },
      {
        name: '净利率',
        type: 'line',
        data: sorted.map((d) => +(d.net_margin * 100).toFixed(1)),
        itemStyle: { color: '#06b6d4' },
        lineStyle: { width: 2 },
        symbol: 'diamond',
        symbolSize: 6,
      },
    ],
  };

  return <ReactEChartsCore option={option} style={{ height }} notMerge />;
}

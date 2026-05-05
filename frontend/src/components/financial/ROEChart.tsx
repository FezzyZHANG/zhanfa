import ReactEChartsCore from 'echarts-for-react';
import type { FinancialData } from '@/types';

interface ROEChartProps {
  data: FinancialData[];
  height?: number;
}

export function ROEChart({ data, height = 300 }: ROEChartProps) {
  const sorted = [...data].sort((a, b) => a.report_date.localeCompare(b.report_date));

  const option = {
    tooltip: {
      trigger: 'axis' as const,
      formatter: (params: Record<string, unknown>[]) => {
        const p = params[0] as { axisValue: string; value: number };
        return `${p.axisValue}<br/>ROE: ${p.value}%`;
      },
    },
    grid: { left: '3%', right: '4%', bottom: '8%', top: '8%', containLabel: true },
    xAxis: {
      type: 'category' as const,
      data: sorted.map((d) => d.report_date),
      axisLabel: { rotate: 30 },
    },
    yAxis: {
      type: 'value' as const,
      name: 'ROE (%)',
      axisLabel: { formatter: '{value}%' },
    },
    series: [
      {
        name: 'ROE',
        type: 'line',
        data: sorted.map((d) => +(d.roe * 100).toFixed(2)),
        itemStyle: { color: '#f59e0b' },
        lineStyle: { width: 3 },
        symbol: 'circle',
        symbolSize: 8,
        markLine: {
          silent: true,
          data: [{ type: 'average' as const, name: '均值' }],
          lineStyle: { color: '#94a3b8', type: 'dashed' as const },
        },
        areaStyle: {
          color: {
            type: 'linear' as const,
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(245,158,11,0.3)' },
              { offset: 1, color: 'rgba(245,158,11,0.02)' },
            ],
          },
        },
      },
    ],
  };

  return <ReactEChartsCore option={option} style={{ height }} notMerge />;
}

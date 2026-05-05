import ReactEChartsCore from 'echarts-for-react';
import type { FinancialData } from '@/types';

interface DebtRatioChartProps {
  data: FinancialData[];
  height?: number;
}

export function DebtRatioChart({ data, height = 300 }: DebtRatioChartProps) {
  const sorted = [...data].sort((a, b) => a.report_date.localeCompare(b.report_date));

  const option = {
    tooltip: {
      trigger: 'axis' as const,
      formatter: (params: Record<string, unknown>[]) => {
        const p0 = params[0] as { axisValue: string; value: number };
        const p1 = params[1] as { value: number };
        return `${p0.axisValue}<br/>资产负债率: ${p0.value}%<br/>流动比率: ${p1.value.toFixed(2)}`;
      },
    },
    legend: { data: ['资产负债率', '流动比率'], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '12%', top: '8%', containLabel: true },
    xAxis: {
      type: 'category' as const,
      data: sorted.map((d) => d.report_date),
      axisLabel: { rotate: 30 },
    },
    yAxis: [
      {
        type: 'value' as const,
        name: '资产负债率(%)',
        axisLabel: { formatter: '{value}%' },
      },
      {
        type: 'value' as const,
        name: '流动比率',
      },
    ],
    series: [
      {
        name: '资产负债率',
        type: 'bar',
        data: sorted.map((d) => +(d.debt_ratio * 100).toFixed(1)),
        itemStyle: {
          color: '#ef4444',
          borderRadius: [4, 4, 0, 0],
        },
        barMaxWidth: 40,
      },
      {
        name: '流动比率',
        type: 'line',
        yAxisIndex: 1,
        data: sorted.map((d) => +d.current_ratio.toFixed(2)),
        itemStyle: { color: '#06b6d4' },
        lineStyle: { width: 2 },
        symbol: 'circle',
        symbolSize: 8,
        markLine: {
          silent: true,
          data: [{ yAxis: 2, name: '安全线', label: { formatter: '安全线 2.0' } }],
          lineStyle: { color: '#22c55e', type: 'dashed' as const },
        },
      },
    ],
  };

  return <ReactEChartsCore option={option} style={{ height }} notMerge />;
}

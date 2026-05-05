import ReactEChartsCore from 'echarts-for-react';
import type { FinancialData } from '@/types';

interface RevenueProfitChartProps {
  data: FinancialData[];
  height?: number;
}

export function RevenueProfitChart({ data, height = 350 }: RevenueProfitChartProps) {
  const sorted = [...data].sort((a, b) => a.report_date.localeCompare(b.report_date));

  const option = {
    tooltip: {
      trigger: 'axis' as const,
      axisPointer: { type: 'cross' as const },
      formatter: (params: Record<string, unknown>[]) => {
        const p0 = params[0] as { axisValue: string };
        const p1 = params[1] as { value: number };
        const p2 = params[2] as { value: number };
        return `${p0.axisValue}<br/>营收: ${p1.value}亿<br/>净利润: ${p2.value}亿`;
      },
    },
    legend: { data: ['营业收入', '净利润'], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '12%', top: '6%', containLabel: true },
    xAxis: {
      type: 'category' as const,
      data: sorted.map((d) => d.report_date),
      axisLabel: { rotate: 30 },
    },
    yAxis: {
      type: 'value' as const,
      name: '金额(亿)',
    },
    series: [
      {
        name: '营业收入',
        type: 'bar',
        data: sorted.map((d) => +(d.revenue / 100_000_000).toFixed(1)),
        itemStyle: { color: '#3b82f6', borderRadius: [4, 4, 0, 0] },
        barMaxWidth: 40,
      },
      {
        name: '净利润',
        type: 'bar',
        data: sorted.map((d) => +(d.net_profit / 100_000_000).toFixed(1)),
        itemStyle: { color: '#22c55e', borderRadius: [4, 4, 0, 0] },
        barMaxWidth: 40,
      },
    ],
  };

  return <ReactEChartsCore option={option} style={{ height }} notMerge />;
}

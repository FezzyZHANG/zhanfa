import ReactEChartsCore from 'echarts-for-react';

interface FinancialChartProps {
  data: { report_date: string; revenue: number; net_profit: number; eps: number; roe: number }[];
  height?: number;
}

export function FinancialChart({ data, height = 350 }: FinancialChartProps) {
  const sorted = [...data].sort(
    (a, b) => a.report_date.localeCompare(b.report_date),
  );

  const option = {
    tooltip: { trigger: 'axis' as const },
    legend: { data: ['营收(亿)', '净利润(亿)', 'ROE(%)'], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '12%', top: '6%', containLabel: true },
    xAxis: {
      type: 'category' as const,
      data: sorted.map((d) => d.report_date),
    },
    yAxis: [
      {
        type: 'value' as const,
        name: '金额(亿)',
        axisLabel: { formatter: '{value}' },
      },
      {
        type: 'value' as const,
        name: 'ROE(%)',
        axisLabel: { formatter: '{value}%' },
      },
    ],
    series: [
      {
        name: '营收(亿)',
        type: 'bar',
        data: sorted.map((d) => +(d.revenue / 100_000_000).toFixed(1)),
        itemStyle: { color: '#3b82f6' },
      },
      {
        name: '净利润(亿)',
        type: 'bar',
        data: sorted.map((d) => +(d.net_profit / 100_000_000).toFixed(1)),
        itemStyle: { color: '#22c55e' },
      },
      {
        name: 'ROE(%)',
        type: 'line',
        yAxisIndex: 1,
        data: sorted.map((d) => +(d.roe * 100).toFixed(1)),
        itemStyle: { color: '#f59e0b' },
        lineStyle: { width: 2 },
      },
    ],
  };

  return <ReactEChartsCore option={option} style={{ height }} notMerge />;
}

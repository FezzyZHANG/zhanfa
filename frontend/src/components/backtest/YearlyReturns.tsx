import ReactECharts from 'echarts-for-react';
import type { YearlyReturn } from '@/types';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';

interface YearlyReturnsProps {
  data: YearlyReturn[];
  height?: number;
}

export function YearlyReturns({ data, height = 250 }: YearlyReturnsProps) {
  const years = data.map((d) => String(d.year));
  const values = data.map((d) => +(d.value * 100).toFixed(2));

  const option = {
    tooltip: {
      trigger: 'axis',
      formatter: (params: { name: string; value: number }[]) => {
        const p = params[0];
        return `${p.name} 年<br/>收益率: ${p.value > 0 ? '+' : ''}${p.value.toFixed(2)}%`;
      },
    },
    grid: { left: 50, right: 20, top: 20, bottom: 30 },
    xAxis: {
      type: 'category',
      data: years,
      axisLine: { lineStyle: { color: '#d1d5db' } },
    },
    yAxis: {
      type: 'value',
      axisLabel: { formatter: (v: number) => `${v}%` },
      splitLine: { lineStyle: { color: 'rgba(107, 114, 128, 0.1)' } },
    },
    series: [
      {
        type: 'bar',
        data: values.map((v: number) => ({
          value: v,
          itemStyle: { color: v >= 0 ? '#ef4444' : '#22c55e' },
        })),
        barMaxWidth: 40,
      },
    ],
  };

  if (data.length === 0) {
    return (
      <Card>
        <CardHeader><CardTitle className="text-sm">年度收益</CardTitle></CardHeader>
        <CardContent><p className="text-muted-foreground text-sm">暂无数据</p></CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">年度收益</CardTitle>
      </CardHeader>
      <CardContent>
        <ReactECharts option={option} style={{ height }} />
      </CardContent>
    </Card>
  );
}

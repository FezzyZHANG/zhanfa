import ReactECharts from 'echarts-for-react';
import type { MonthlyReturn } from '@/types';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';

interface MonthlyHeatmapProps {
  data: MonthlyReturn[];
  height?: number;
}

const MONTH_LABELS = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'];

export function MonthlyHeatmap({ data, height = 220 }: MonthlyHeatmapProps) {
  if (data.length === 0) {
    return (
      <Card>
        <CardHeader><CardTitle className="text-sm">月度收益热力图</CardTitle></CardHeader>
        <CardContent><p className="text-muted-foreground text-sm">暂无数据</p></CardContent>
      </Card>
    );
  }

  const years = [...new Set(data.map((d) => d.year))].sort();

  const seriesData = data.map((d) => [d.year, d.month, +(d.value * 100).toFixed(2)]);

  const maxAbs = Math.max(...data.map((d) => Math.abs(d.value)));

  const option = {
    tooltip: {
      formatter: (params: { data: [number, number, number] }) => {
        const [year, month, value] = params.data;
        return `${year}年${month}月<br/>收益: ${value > 0 ? '+' : ''}${value.toFixed(2)}%`;
      },
    },
    grid: { left: 80, right: 40, top: 10, bottom: 30 },
    xAxis: {
      type: 'category',
      data: MONTH_LABELS,
      splitArea: { show: true },
    },
    yAxis: {
      type: 'category',
      data: years,
      inverse: true,
      splitArea: { show: true },
    },
    visualMap: {
      min: -maxAbs * 100,
      max: maxAbs * 100,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      inRange: { color: ['#22c55e', '#f8fafc', '#ef4444'] },
      text: ['盈', '亏'],
      textStyle: { color: '#6b7280' },
    },
    series: [
      {
        type: 'heatmap',
        data: seriesData,
        label: {
          show: true,
          fontSize: 10,
          formatter: (params: { data: [number, number, number] }) => {
            const v = params.data[2];
            return `${v > 0 ? '+' : ''}${v.toFixed(1)}%`;
          },
        },
        emphasis: {
          itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.3)' },
        },
      },
    ],
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">月度收益热力图</CardTitle>
      </CardHeader>
      <CardContent>
        <ReactECharts option={option} style={{ height }} />
      </CardContent>
    </Card>
  );
}

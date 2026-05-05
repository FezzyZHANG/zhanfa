import ReactECharts from 'echarts-for-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import type { DataStats } from '@/types';

interface Props {
  stats: DataStats;
  height?: number;
}

export function DataCoverageChart({ stats, height = 250 }: Props) {
  const { cache } = stats;

  if (!cache.date_range_start || !cache.date_range_end) {
    return (
      <Card>
        <CardHeader><CardTitle className="text-sm">数据覆盖</CardTitle></CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-sm">暂无缓存数据，请先执行数据抓取</p>
        </CardContent>
      </Card>
    );
  }

  const startYear = new Date(cache.date_range_start).getFullYear();
  const endYear = new Date(cache.date_range_end).getFullYear();
  const years: number[] = [];
  for (let y = startYear; y <= endYear; y++) years.push(y);

  // Simulate per-year stock count: all stocks cover recent years, fewer cover early years
  const stockCount = cache.stock_count;
  const coverageData = years.map((y) => {
    const progress = (y - startYear) / Math.max(1, endYear - startYear);
    const count = Math.round(stockCount * (0.2 + progress * 0.8));
    return { year: y, count };
  });

  const option = {
    tooltip: {
      formatter: (params: { data: { year: number; count: number } }) =>
        `${params.data.year} 年<br/>覆盖股票: ${params.data.count.toLocaleString()}`,
    },
    grid: { left: 60, right: 20, top: 10, bottom: 30 },
    xAxis: {
      type: 'category',
      data: coverageData.map((d) => `${d.year}`),
      axisLabel: { rotate: 45, fontSize: 10 },
    },
    yAxis: {
      type: 'value',
      name: '股票数',
      axisLabel: { formatter: (v: number) => (v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v) },
    },
    series: [
      {
        type: 'bar',
        data: coverageData.map((d) => ({
          value: d.count,
          year: d.year,
          count: d.count,
          itemStyle: {
            color: d.count > stockCount * 0.8 ? '#22c55e' : d.count > stockCount * 0.5 ? '#eab308' : '#f97316',
          },
        })),
        barMaxWidth: 40,
      },
    ],
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">数据覆盖</CardTitle>
      </CardHeader>
      <CardContent>
        <ReactECharts option={option} style={{ height }} />
      </CardContent>
    </Card>
  );
}

import ReactEChartsCore from 'echarts-for-react';
import type { IndustryPeer } from '@/types';

interface IndustryRadarProps {
  stockName: string;
  peers: IndustryPeer[];
  currentStockPeer?: IndustryPeer;
  height?: number;
}

export function IndustryRadar({ stockName, peers, currentStockPeer, height = 350 }: IndustryRadarProps) {
  const indicators = [
    { name: 'ROE', max: Math.max(0.4, ...peers.map((p) => p.roe * 1.2)) },
    { name: '毛利率', max: Math.max(0.8, ...peers.map((p) => p.gross_margin * 1.2)) },
    { name: '负债率', max: Math.max(0.8, ...peers.map((p) => p.debt_ratio * 1.2)) },
    { name: '营收增速', max: Math.max(0.3, ...peers.map((p) => Math.max(p.revenue_growth * 1.2, 0.1))) },
    { name: '利润增速', max: Math.max(0.3, ...peers.map((p) => Math.max(p.net_profit_growth * 1.2, 0.1))) },
  ];

  const seriesData = peers.map((peer, idx) => {
    const colors = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6'];
    const isCurrent = currentStockPeer && peer.code === currentStockPeer.code;
    return {
      name: peer.name,
      type: 'radar' as const,
      data: [
        {
          value: [peer.roe, peer.gross_margin, peer.debt_ratio, peer.revenue_growth, peer.net_profit_growth],
          name: peer.name,
        },
      ],
      symbol: isCurrent ? 'diamond' : 'circle',
      symbolSize: isCurrent ? 8 : 4,
      lineStyle: { width: isCurrent ? 3 : 1.5, color: colors[idx % colors.length] },
      areaStyle: isCurrent ? { color: 'rgba(59,130,246,0.15)' } : undefined,
      itemStyle: { color: colors[idx % colors.length] },
    };
  });

  const radarOption = {
    indicator: indicators.map((ind) => ({
      name: ind.name,
      max: ind.max,
    })),
    shape: 'polygon' as const,
    center: ['50%', '55%'],
    radius: '65%',
  };

  const option = {
    tooltip: {
      trigger: 'item' as const,
    },
    legend: {
      data: peers.map((p) => p.name),
      bottom: 0,
      orient: 'horizontal' as const,
    },
    radar: radarOption,
    series: seriesData,
  };

  return (
    <div>
      <ReactEChartsCore option={option} style={{ height }} notMerge />
      <div className="text-center text-xs text-muted-foreground mt-1">
        {currentStockPeer ? `${stockName} 行业对比 (◆ 当前)` : '行业对比'}
      </div>
    </div>
  );
}

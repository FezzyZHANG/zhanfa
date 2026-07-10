import type { QuoteItem } from '@/types';

function freshnessLabel(freshness: string | undefined): string {
  if (!freshness || freshness === 'unknown') return '未知';
  if (freshness === 'live') return '实时';
  if (freshness === 'stale') return '已过期';
  if (freshness.startsWith('cached_')) {
    const suffix = freshness.slice(7);
    return `缓存 ${suffix}`;
  }
  return freshness;
}

export function DataStatusBadge({
  status,
  freshness,
}: {
  status: QuoteItem['data_status'];
  freshness?: string;
}) {
  if (!status) {
    return <span title="无数据" className="inline-block w-2.5 h-2.5 rounded-full bg-gray-400" />;
  }

  const { has_daily, has_financial, daily_start, daily_end, financial_periods } = status;
  let color = 'bg-red-500';
  let label = '无缓存数据';
  if (has_daily && has_financial) {
    color = 'bg-green-500';
    label = '有日线+财务数据';
  } else if (has_daily) {
    color = 'bg-yellow-500';
    label = '仅有日线数据';
  }

  const details = [
    has_daily && daily_start && daily_end ? `日线: ${daily_start} ~ ${daily_end}` : '',
    has_financial ? `财务: ${financial_periods} 期` : '',
    freshness ? `新鲜度: ${freshnessLabel(freshness)}` : '',
  ].filter(Boolean).join('\n');

  return (
    <span
      title={`${label}${details ? '\n' + details : ''}`}
      className={`inline-block w-2.5 h-2.5 rounded-full ${color} cursor-help`}
    />
  );
}

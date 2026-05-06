import { useState, useMemo } from 'react';
import { useNavigate } from '@tanstack/react-router';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import type { StockDataStatus } from '@/types';

interface Props {
  data: StockDataStatus[];
  loading?: boolean;
}

type SortKey = 'code' | 'name' | 'daily_rows' | 'daily_end' | 'financial_rows' | 'cached_at';
type SortValue = string | number;

function fmtRelativeTime(isoStr: string | null): string {
  if (!isoStr) return '—';
  const now = Date.now();
  const then = new Date(isoStr).getTime();
  const diffMs = now - then;
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return '刚刚';
  if (diffMin < 60) return `${diffMin}分钟`;
  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) return `${diffHour}小时`;
  const diffDay = Math.floor(diffHour / 24);
  if (diffDay < 30) return `${diffDay}天`;
  const diffMonth = Math.floor(diffDay / 30);
  return `${diffMonth}月`;
}

export function StockDataTable({ data, loading }: Props) {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('code');
  const [sortAsc, setSortAsc] = useState(true);
  const [filter, setFilter] = useState<'all' | 'no-financial' | 'old-data' | 'in-watchlist'>('all');

  const filtered = useMemo(() => {
    let result = [...data];

    if (search) {
      const kw = search.toLowerCase();
      result = result.filter((s) => s.code.includes(kw) || s.name.toLowerCase().includes(kw));
    }

    if (filter === 'no-financial') result = result.filter((s) => !s.has_financial);
    else if (filter === 'old-data') {
      const thirtyDaysAgo = new Date();
      thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
      const cutoff = thirtyDaysAgo.toISOString().slice(0, 10);
      result = result.filter((s) => s.daily_end && s.daily_end < cutoff);
    } else if (filter === 'in-watchlist') {
      result = result.filter((s) => s.in_watchlist.length > 0);
    }

    result.sort((a, b) => {
      let va: SortValue;
      let vb: SortValue;
      if (sortKey === 'daily_end') {
        va = a.daily_end ?? '';
        vb = b.daily_end ?? '';
      } else if (sortKey === 'financial_rows') {
        va = a.financial_rows;
        vb = b.financial_rows;
      } else if (sortKey === 'daily_rows') {
        va = a.daily_rows;
        vb = b.daily_rows;
      } else if (sortKey === 'cached_at') {
        va = a.daily_cached_at ?? '';
        vb = b.daily_cached_at ?? '';
      } else if (sortKey === 'name') {
        va = a.name;
        vb = b.name;
      } else {
        va = a.code;
        vb = b.code;
      }
      const cmp = va < vb ? -1 : va > vb ? 1 : 0;
      return sortAsc ? cmp : -cmp;
    });

    return result;
  }, [data, search, sortKey, sortAsc, filter]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) setSortAsc(!sortAsc);
    else {
      setSortKey(key);
      setSortAsc(true);
    }
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <CardTitle className="text-sm">股票数据详情</CardTitle>
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="搜索代码或名称..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="h-8 px-2 text-xs border border-border rounded-lg bg-background w-40"
            />
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value as typeof filter)}
              className="h-8 px-2 text-xs border border-border rounded-lg bg-background"
            >
              <option value="all">全部</option>
              <option value="no-financial">缺少财务数据</option>
              <option value="old-data">数据过旧</option>
              <option value="in-watchlist">在自选中</option>
            </select>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <p className="text-sm text-muted-foreground">加载中...</p>
        ) : filtered.length === 0 ? (
          <p className="text-sm text-muted-foreground">暂无数据</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border text-left text-muted-foreground">
                  <th className="py-2 pr-3 cursor-pointer select-none whitespace-nowrap" onClick={() => handleSort('code')}>
                    代码 <SortIcon sortKey={sortKey} sortAsc={sortAsc} col="code" />
                  </th>
                  <th className="py-2 pr-3 cursor-pointer select-none whitespace-nowrap" onClick={() => handleSort('name')}>
                    名称 <SortIcon sortKey={sortKey} sortAsc={sortAsc} col="name" />
                  </th>
                  <th className="py-2 pr-3 whitespace-nowrap">自选组</th>
                  <th className="py-2 pr-3 cursor-pointer select-none whitespace-nowrap" onClick={() => handleSort('daily_end')}>
                    日线截止 <SortIcon sortKey={sortKey} sortAsc={sortAsc} col="daily_end" />
                  </th>
                  <th className="py-2 pr-3 cursor-pointer select-none whitespace-nowrap" onClick={() => handleSort('daily_rows')}>
                    日线行数 <SortIcon sortKey={sortKey} sortAsc={sortAsc} col="daily_rows" />
                  </th>
                  <th className="py-2 pr-3 cursor-pointer select-none whitespace-nowrap" onClick={() => handleSort('financial_rows')}>
                    财务行数 <SortIcon sortKey={sortKey} sortAsc={sortAsc} col="financial_rows" />
                  </th>
                  <th className="py-2 pr-3 cursor-pointer select-none whitespace-nowrap" onClick={() => handleSort('cached_at')}>
                    缓存时间 <SortIcon sortKey={sortKey} sortAsc={sortAsc} col="cached_at" />
                  </th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((s) => (
                  <tr
                    key={s.code}
                    className="border-b border-border hover:bg-accent/50 cursor-pointer"
                    onClick={() => navigate({ to: '/stock/$stockCode', params: { stockCode: s.code } })}
                  >
                    <td className="py-2 pr-3 font-mono">{s.code}</td>
                    <td className="py-2 pr-3">{s.name || '—'}</td>
                    <td className="py-2 pr-3 text-muted-foreground">
                      {s.in_watchlist.length > 0 ? s.in_watchlist.join(', ') : '—'}
                    </td>
                    <td className="py-2 pr-3">
                      {s.has_daily && s.daily_end ? (
                        <span className={isStale(s.daily_end) ? 'text-orange-500' : ''}>
                          {s.daily_end}
                        </span>
                      ) : (
                        <span className="text-red-500">无</span>
                      )}
                    </td>
                    <td className="py-2 pr-3">{s.has_daily ? s.daily_rows.toLocaleString() : '—'}</td>
                    <td className="py-2 pr-3">{s.has_financial ? s.financial_rows.toLocaleString() : <span className="text-red-500">无</span>}</td>
                    <td className="py-2 pr-3 text-muted-foreground text-[11px]">
                      {s.daily_cached_at ? fmtRelativeTime(s.daily_cached_at) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function SortIcon({ col, sortKey, sortAsc }: { col: SortKey; sortKey: SortKey; sortAsc: boolean }) {
  if (sortKey !== col) return <span className="text-muted-foreground ml-1">↕</span>;
  return <span className="ml-1">{sortAsc ? '↑' : '↓'}</span>;
}

function isStale(dateStr: string): boolean {
  const d = new Date(dateStr);
  const thirtyDaysAgo = new Date();
  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
  return d < thirtyDaysAgo;
}

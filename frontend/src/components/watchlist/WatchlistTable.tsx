import { useState, useMemo } from 'react';
import type { QuoteItem } from '@/types';
import { formatNumber, formatPercent } from '@/lib/utils';
import { useNavigate } from '@tanstack/react-router';
import { Button } from '@/components/ui/Button';
import { useWatchlistUrlFilters, type SortKey } from '@/hooks/useWatchlistUrlFilters';

interface WatchlistTableProps {
  quotes: QuoteItem[];
  onRemove: (code: string) => void;
  onBatchRemove: (codes: string[]) => void;
  onEditNotes: (code: string, currentNotes: string | null) => void;
}

function DataStatusIcon({ status }: { status: QuoteItem['data_status'] }) {
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
  ].filter(Boolean).join('\n');

  return (
    <span
      title={`${label}${details ? '\n' + details : ''}`}
      className={`inline-block w-2.5 h-2.5 rounded-full ${color} cursor-help`}
    />
  );
}

export function WatchlistTable({ quotes, onRemove, onBatchRemove, onEditNotes }: WatchlistTableProps) {
  const navigate = useNavigate();
  const {
    sortKey, sortDir, searchText, peMin, peMax, changeDir,
    setSort, setSearchText, setPeRange, setChangeFilter, applyFilters,
  } = useWatchlistUrlFilters();
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSort(key, sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setSort(key, 'asc');
    }
  };

  const filtered = useMemo(() => applyFilters(quotes), [quotes, applyFilters]);

  const sorted = useMemo(() => {
    const arr = [...filtered];
    arr.sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];
      const aNum = aVal != null ? Number(aVal) : -Infinity;
      const bNum = bVal != null ? Number(bVal) : -Infinity;

      let cmp: number;
      if (sortKey === 'code' || sortKey === 'name') {
        cmp = String(aVal || '').localeCompare(String(bVal || ''), 'zh-CN');
      } else {
        cmp = aNum - bNum;
      }

      return sortDir === 'asc' ? cmp : -cmp;
    });
    return arr;
  }, [filtered, sortKey, sortDir]);

  const toggleSelect = (code: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(code)) next.delete(code); else next.add(code);
      return next;
    });
  };

  const toggleAll = () => {
    if (selected.size === sorted.length && sorted.length > 0) {
      setSelected(new Set());
    } else {
      setSelected(new Set(sorted.map((s) => s.code)));
    }
  };

  const handleBatchRemove = () => {
    if (selected.size === 0) return;
    onBatchRemove(Array.from(selected));
    setSelected(new Set());
  };

  const SortHeader = ({ label, sKey }: { label: string; sKey: SortKey }) => (
    <th
      className="py-3 px-3 text-left text-xs font-medium text-muted-foreground cursor-pointer select-none hover:text-foreground whitespace-nowrap"
      onClick={() => handleSort(sKey)}
    >
      {label} {sortKey === sKey ? (sortDir === 'asc' ? '↑' : '↓') : ''}
    </th>
  );

  return (
    <div>
      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <input
          className="rounded-md border border-border bg-background px-3 py-1.5 text-sm w-48 focus:outline-none focus:ring-2 focus:ring-primary"
          placeholder="搜索代码/名称..."
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
        />
        <div className="flex items-center gap-1 text-xs text-muted-foreground">
          PE
          <input
            className="rounded-md border border-border bg-background px-2 py-1 text-xs w-20 focus:outline-none focus:ring-1 focus:ring-primary"
            placeholder="min"
            value={peMin != null ? String(peMin) : ''}
            onChange={(e) => setPeRange(e.target.value, peMax != null ? String(peMax) : '')}
          />
          <span>—</span>
          <input
            className="rounded-md border border-border bg-background px-2 py-1 text-xs w-20 focus:outline-none focus:ring-1 focus:ring-primary"
            placeholder="max"
            value={peMax != null ? String(peMax) : ''}
            onChange={(e) => setPeRange(peMin != null ? String(peMin) : '', e.target.value)}
          />
        </div>
        <select
          className="rounded-md border border-border bg-background px-2 py-1.5 text-xs focus:outline-none"
          value={changeDir}
          onChange={(e) => setChangeFilter(e.target.value)}
        >
          <option value="">全部涨跌</option>
          <option value="up">上涨</option>
          <option value="down">下跌</option>
        </select>
        {selected.size > 0 && (
          <Button variant="destructive" size="sm" onClick={handleBatchRemove}>
            移除所选 ({selected.size})
          </Button>
        )}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              <th className="py-3 px-3 w-8">
                <input
                  type="checkbox"
                  className="rounded"
                  checked={sorted.length > 0 && selected.size === sorted.length}
                  onChange={toggleAll}
                />
              </th>
              <th className="py-3 px-3 w-8" />
              <SortHeader label="代码" sKey="code" />
              <SortHeader label="名称" sKey="name" />
              <SortHeader label="最新价" sKey="latest_price" />
              <SortHeader label="涨跌幅" sKey="change_pct" />
              <SortHeader label="PE" sKey="pe" />
              <SortHeader label="PB" sKey="pb" />
              <SortHeader label="股息率" sKey="dividend_yield" />
              <th className="py-3 px-3 text-left text-xs font-medium text-muted-foreground whitespace-nowrap">备注</th>
              <th className="py-3 px-3 text-left text-xs font-medium text-muted-foreground whitespace-nowrap">操作</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((item) => (
              <tr
                key={item.code}
                className="border-b border-border hover:bg-accent/50 cursor-pointer"
                onClick={() => navigate({ to: '/stock/$stockCode', params: { stockCode: item.code } })}
              >
                <td className="py-3 px-3" onClick={(e) => e.stopPropagation()}>
                  <input
                    type="checkbox"
                    className="rounded"
                    checked={selected.has(item.code)}
                    onChange={() => toggleSelect(item.code)}
                  />
                </td>
                <td className="py-3 px-3">
                  <DataStatusIcon status={item.data_status} />
                </td>
                <td className="py-3 px-3 font-mono text-xs">{item.code}</td>
                <td className="py-3 px-3 font-medium">{item.name || '--'}</td>
                <td className="py-3 px-3 font-mono text-right">
                  {item.latest_price != null ? formatNumber(item.latest_price) : '--'}
                </td>
                <td className={`py-3 px-3 font-mono text-right ${item.change_pct != null ? (item.change_pct >= 0 ? 'text-red-500' : 'text-green-500') : ''}`}>
                  {item.change_pct != null ? formatPercent(item.change_pct) : '--'}
                </td>
                <td className="py-3 px-3 font-mono text-right">
                  {item.pe != null ? item.pe.toFixed(1) : '--'}
                </td>
                <td className="py-3 px-3 font-mono text-right">
                  {item.pb != null ? item.pb.toFixed(1) : '--'}
                </td>
                <td className="py-3 px-3 font-mono text-right">
                  {item.dividend_yield != null ? formatPercent(item.dividend_yield) : '--'}
                </td>
                <td className="py-3 px-3 text-xs text-muted-foreground max-w-[120px] truncate">
                  <span
                    className="cursor-pointer hover:text-foreground"
                    onClick={(e) => { e.stopPropagation(); onEditNotes(item.code, item.notes); }}
                  >
                    {item.notes || '--'}
                  </span>
                </td>
                <td className="py-3 px-3" onClick={(e) => e.stopPropagation()}>
                  <Button variant="ghost" size="sm" onClick={() => onRemove(item.code)}>
                    移除
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {sorted.length === 0 && (
          <p className="text-center text-muted-foreground py-12">
            {quotes.length === 0 ? '暂无股票，点击"添加股票"开始' : '无匹配结果'}
          </p>
        )}
      </div>
    </div>
  );
}

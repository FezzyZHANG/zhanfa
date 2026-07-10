import { useState, useMemo } from 'react';
import type { Trade } from '@/types';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { exportToCsv, formatNumber } from '@/lib/utils';

interface TradeTableProps {
  trades: Trade[];
  pageSize?: number;
}

export function TradeTable({ trades, pageSize = 15 }: TradeTableProps) {
  const [page, setPage] = useState(0);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  const filtered = useMemo(() => {
    return trades.filter((t) => {
      if (dateFrom && t.date < dateFrom) return false;
      if (dateTo && t.date > dateTo) return false;
      return true;
    });
  }, [trades, dateFrom, dateTo]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const paged = filtered.slice(page * pageSize, (page + 1) * pageSize);

  const exportCSV = () => {
    exportToCsv(
      'trades.csv',
      ['日期', '方向', '价格', '数量', '盈亏'],
      filtered.map((t) => [t.date, t.action === 'buy' ? '买入' : '卖出', t.price, t.quantity, t.pnl]),
    );
  };

  const totalPnl = filtered.reduce((sum, t) => sum + (t.pnl ?? 0), 0);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between flex-wrap gap-2">
          <CardTitle className="text-sm">交易记录 ({filtered.length} 笔)</CardTitle>
          <Button variant="outline" size="sm" onClick={exportCSV}>
            导出 CSV
          </Button>
        </div>
        <div className="flex gap-2 mt-2">
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => { setDateFrom(e.target.value); setPage(0); }}
            className="border border-border rounded-md px-2 py-1 text-xs bg-transparent"
          />
          <span className="text-xs text-muted-foreground self-center">至</span>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => { setDateTo(e.target.value); setPage(0); }}
            className="border border-border rounded-md px-2 py-1 text-xs bg-transparent"
          />
          {(dateFrom || dateTo) && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => { setDateFrom(''); setDateTo(''); setPage(0); }}
            >
              清除
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-3 px-4 font-medium text-muted-foreground">日期</th>
              <th className="text-left py-3 px-4 font-medium text-muted-foreground">方向</th>
              <th className="text-right py-3 px-4 font-medium text-muted-foreground">价格</th>
              <th className="text-right py-3 px-4 font-medium text-muted-foreground">数量</th>
              <th className="text-right py-3 px-4 font-medium text-muted-foreground">盈亏</th>
            </tr>
          </thead>
          <tbody>
            {paged.map((trade, idx) => (
              <tr key={idx} className="border-b border-border">
                <td className="py-3 px-4">{trade.date}</td>
                <td className="py-3 px-4">
                  <span
                    className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                      trade.action === 'buy' ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'
                    }`}
                  >
                    {trade.action === 'buy' ? '买入' : '卖出'}
                  </span>
                </td>
                <td className="text-right py-3 px-4 font-mono">{trade.price.toFixed(2)}</td>
                <td className="text-right py-3 px-4 font-mono">{formatNumber(trade.quantity)}</td>
                <td
                  className={`text-right py-3 px-4 font-mono ${
                    trade.pnl !== undefined && trade.pnl >= 0
                      ? 'text-green-600'
                      : trade.pnl !== undefined
                        ? 'text-red-500'
                        : 'text-muted-foreground'
                  }`}
                >
                  {trade.pnl !== undefined ? `${trade.pnl >= 0 ? '+' : ''}${formatNumber(trade.pnl)}` : '-'}
                </td>
              </tr>
            ))}
            {paged.length === 0 && (
              <tr>
                <td colSpan={5} className="text-center py-8 text-muted-foreground">
                  暂无交易记录
                </td>
              </tr>
            )}
          </tbody>
          <tfoot>
            <tr className="border-t border-border">
              <td colSpan={4} className="text-right py-3 px-4 font-medium">合计盈亏</td>
              <td className={`text-right py-3 px-4 font-mono font-bold ${totalPnl >= 0 ? 'text-green-600' : 'text-red-500'}`}>
                {totalPnl >= 0 ? '+' : ''}{formatNumber(totalPnl)}
              </td>
            </tr>
          </tfoot>
        </table>
        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-4">
            <span className="text-xs text-muted-foreground">
              第 {page + 1} / {totalPages} 页
            </span>
            <div className="flex gap-1">
              <Button variant="outline" size="sm" disabled={page === 0} onClick={() => setPage(page - 1)}>
                上一页
              </Button>
              <Button variant="outline" size="sm" disabled={page >= totalPages - 1} onClick={() => setPage(page + 1)}>
                下一页
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

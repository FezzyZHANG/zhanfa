import { useMemo, useState } from 'react';
import { Button } from '@/components/ui/Button';
import { formatNumber, formatPercent } from '@/lib/utils';
import type { FinancialData } from '@/types';

interface FinancialTableProps {
  data: FinancialData[];
}

type SortField = keyof FinancialData;
type SortDir = 'asc' | 'desc';

const COLUMNS: { field: SortField; label: string; format: (v: number) => string }[] = [
  { field: 'report_date', label: '报告期', format: (v) => String(v) },
  { field: 'revenue', label: '营收(亿)', format: (v) => formatNumber(v / 100_000_000) },
  { field: 'net_profit', label: '净利润(亿)', format: (v) => formatNumber(v / 100_000_000) },
  { field: 'eps', label: 'EPS', format: (v) => v.toFixed(2) },
  { field: 'roe', label: 'ROE', format: (v) => formatPercent(v) },
  { field: 'gross_margin', label: '毛利率', format: (v) => formatPercent(v) },
  { field: 'net_margin', label: '净利率', format: (v) => formatPercent(v) },
  { field: 'debt_ratio', label: '资产负债率', format: (v) => formatPercent(v) },
  { field: 'current_ratio', label: '流动比率', format: (v) => v.toFixed(2) },
  { field: 'dividend_yield', label: '股息率', format: (v) => formatPercent(v) },
  { field: 'pe', label: 'PE', format: (v) => v.toFixed(1) },
  { field: 'pb', label: 'PB', format: (v) => v.toFixed(1) },
];

export function FinancialTable({ data }: FinancialTableProps) {
  const [sortField, setSortField] = useState<SortField>('report_date');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  const sorted = useMemo(() => {
    return [...data].sort((a, b) => {
      const aVal = a[sortField];
      const bVal = b[sortField];
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortDir === 'asc' ? aVal - bVal : bVal - aVal;
      }
      const cmp = String(aVal).localeCompare(String(bVal));
      return sortDir === 'asc' ? cmp : -cmp;
    });
  }, [data, sortField, sortDir]);

  function handleSort(field: SortField) {
    if (field === sortField) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDir(field === 'report_date' ? 'desc' : 'asc');
    }
  }

  function exportCSV() {
    const headers = COLUMNS.map((c) => c.label).join(',');
    const rows = sorted.map((row) =>
      COLUMNS.map((c) => {
        if (c.field === 'report_date') return row.report_date;
        return row[c.field];
      }).join(','),
    );
    const csv = '﻿' + [headers, ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'financial_data.csv';
    a.click();
    URL.revokeObjectURL(url);
  }

  const sortIndicator = (field: SortField) => {
    if (field !== sortField) return '';
    return sortDir === 'asc' ? ' ▲' : ' ▼';
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-sm font-medium text-muted-foreground">
          共 {data.length} 期财报数据
        </h3>
        <Button variant="outline" size="sm" onClick={exportCSV}>
          导出 CSV
        </Button>
      </div>
      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-muted/50">
              {COLUMNS.map((col) => (
                <th
                  key={col.field}
                  className="text-left py-2 px-3 font-medium text-muted-foreground cursor-pointer hover:text-foreground whitespace-nowrap select-none"
                  onClick={() => handleSort(col.field)}
                >
                  {col.label}{sortIndicator(col.field)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((row) => (
              <tr key={row.report_date} className="border-t border-border hover:bg-muted/30">
                {COLUMNS.map((col) => (
                  <td key={col.field} className="py-2 px-3 font-mono whitespace-nowrap">
                    {col.format(row[col.field] as number)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

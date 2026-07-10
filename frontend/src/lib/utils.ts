import { type ClassValue, clsx } from 'clsx';

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

export function formatCurrency(value: number): string {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: 'CNY',
    minimumFractionDigits: 2,
  }).format(value);
}

export function formatPercent(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat('zh-CN').format(value);
}

export function formatDate(date: string): string {
  return new Date(date).toLocaleDateString('zh-CN');
}

export function exportToCsv(filename: string, headers: string[], rows: (string | number | null | undefined)[][]) {
  const escapeCell = (value: string | number | null | undefined) => {
    const text = value == null ? '' : String(value);
    return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
  };
  const csv = [headers, ...rows]
    .map((row) => row.map(escapeCell).join(','))
    .join('\n');
  const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

const CATEGORY_LABELS: Record<string, string> = {
  trend: '趋势跟踪',
  momentum: '动量',
  fundamental: '基本面',
  composite: '复合策略',
};

export function getCategoryLabel(category: string): string {
  return CATEGORY_LABELS[category] || category;
}

const CATEGORY_COLORS: Record<string, string> = {
  trend: 'bg-blue-100 text-blue-800',
  momentum: 'bg-orange-100 text-orange-800',
  fundamental: 'bg-green-100 text-green-800',
  composite: 'bg-purple-100 text-purple-800',
};

export function getCategoryColor(category: string): string {
  return CATEGORY_COLORS[category] || 'bg-gray-100 text-gray-800';
}

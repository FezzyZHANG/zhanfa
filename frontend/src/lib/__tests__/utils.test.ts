import { describe, it, expect } from 'vitest';
import {
  cn,
  formatCurrency,
  formatPercent,
  formatNumber,
  formatDate,
  getCategoryLabel,
  getCategoryColor,
} from '@/lib/utils';

describe('cn', () => {
  it('merges class strings', () => {
    expect(cn('a', 'b')).toBe('a b');
  });

  it('filters falsy values', () => {
    expect(cn('a', false && 'b', undefined, 'c')).toBe('a c');
  });

  it('handles conditional classes', () => {
    expect(cn('base', true && 'active', false && 'hidden')).toBe('base active');
  });

  it('returns empty string for no inputs', () => {
    expect(cn()).toBe('');
  });
});

describe('formatCurrency', () => {
  it('formats CNY currency', () => {
    const result = formatCurrency(1234.56);
    expect(result).toContain('1,234.56');
  });

  it('formats zero', () => {
    const result = formatCurrency(0);
    expect(result).toContain('0.00');
  });

  it('formats negative values', () => {
    const result = formatCurrency(-500);
    expect(result).toContain('500.00');
  });
});

describe('formatPercent', () => {
  it('formats percentage', () => {
    expect(formatPercent(0.1234)).toBe('12.34%');
  });

  it('formats zero', () => {
    expect(formatPercent(0)).toBe('0.00%');
  });

  it('formats negative', () => {
    expect(formatPercent(-0.05)).toBe('-5.00%');
  });

  it('handles values over 1', () => {
    expect(formatPercent(1.5)).toBe('150.00%');
  });
});

describe('formatNumber', () => {
  it('formats with zh-CN locale', () => {
    const result = formatNumber(1234567);
    expect(result).toBe('1,234,567');
  });

  it('formats zero', () => {
    expect(formatNumber(0)).toBe('0');
  });

  it('formats decimals', () => {
    const result = formatNumber(1234.5);
    expect(result).toBe('1,234.5');
  });
});

describe('formatDate', () => {
  it('formats ISO date string to zh-CN', () => {
    const result = formatDate('2024-03-15');
    expect(result).toContain('2024');
  });
});

describe('getCategoryLabel', () => {
  it('returns label for known category', () => {
    expect(getCategoryLabel('trend')).toBe('趋势跟踪');
    expect(getCategoryLabel('momentum')).toBe('动量');
    expect(getCategoryLabel('fundamental')).toBe('基本面');
    expect(getCategoryLabel('composite')).toBe('复合策略');
  });

  it('returns raw string for unknown category', () => {
    expect(getCategoryLabel('unknown')).toBe('unknown');
  });
});

describe('getCategoryColor', () => {
  it('returns tailwind classes for known category', () => {
    expect(getCategoryColor('trend')).toContain('bg-blue-100');
    expect(getCategoryColor('momentum')).toContain('bg-orange-100');
    expect(getCategoryColor('fundamental')).toContain('bg-green-100');
    expect(getCategoryColor('composite')).toContain('bg-purple-100');
  });

  it('returns gray fallback for unknown category', () => {
    expect(getCategoryColor('unknown')).toContain('bg-gray-100');
  });
});

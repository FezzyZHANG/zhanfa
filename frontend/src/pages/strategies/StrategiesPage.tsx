import { useStrategies } from '@/hooks/useStrategies';
import { StrategyList } from '@/components/strategy/StrategyList';
import { Button } from '@/components/ui/Button';
import { useState, useMemo } from 'react';
import type { Strategy, StrategyCategory } from '@/types';
import { useNavigate } from '@tanstack/react-router';

const CATEGORIES: { key: StrategyCategory | 'all'; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: 'trend', label: '趋势跟踪' },
  { key: 'momentum', label: '动量' },
  { key: 'fundamental', label: '基本面' },
  { key: 'composite', label: '复合策略' },
];

export function StrategiesPage() {
  const { data: strategiesData, isLoading } = useStrategies();
  const [filter, setFilter] = useState<StrategyCategory | 'all'>('all');
  const [search, setSearch] = useState('');
  const navigate = useNavigate();

  const filtered = useMemo(() => {
    const strategies = Array.isArray(strategiesData) ? (strategiesData as Strategy[]) : [];
    let result = filter === 'all'
      ? strategies
      : strategies.filter((s) => s.category === filter);

    if (search.trim()) {
      const kw = search.trim().toLowerCase();
      result = result.filter(
        (s) =>
          s.name.toLowerCase().includes(kw) ||
          s.description.toLowerCase().includes(kw)
      );
    }
    return result;
  }, [strategiesData, filter, search]);

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight mb-2">策略列表</h1>
        <p className="text-muted-foreground">
          浏览所有交易策略，按分类筛选并查看详细信息
        </p>
      </div>

      <div className="flex flex-col sm:flex-row sm:items-center gap-4 mb-6">
        <div className="flex flex-wrap gap-2">
          {CATEGORIES.map((cat) => (
            <Button
              key={cat.key}
              variant={filter === cat.key ? 'default' : 'outline'}
              size="sm"
              onClick={() => setFilter(cat.key)}
            >
              {cat.label}
            </Button>
          ))}
        </div>
        <div className="relative flex-1 max-w-xs">
          <input
            type="text"
            placeholder="搜索策略名称或描述..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          />
        </div>
      </div>

      {filtered && filtered.length === 0 && !isLoading ? (
        <div className="text-center py-12 text-muted-foreground">
          没有找到匹配的策略
        </div>
      ) : (
      <StrategyList
          strategies={filtered}
          isLoading={isLoading}
          onStrategyClick={(id) => navigate({ to: '/strategies/$strategyId', params: { strategyId: String(id) } })}
        />
      )}
    </div>
  );
}

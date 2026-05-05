import { StrategyCard } from './StrategyCard';
import { Skeleton } from '@/components/ui/Skeleton';
import type { Strategy } from '@/types';

interface StrategyListProps {
  strategies: Strategy[];
  isLoading?: boolean;
  onStrategyClick?: (id: number) => void;
}

export function StrategyList({ strategies, isLoading, onStrategyClick }: StrategyListProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-40 rounded-xl" />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {strategies.map((s) => (
        <StrategyCard
          key={s.id}
          strategy={s}
          onClick={() => onStrategyClick?.(s.id)}
        />
      ))}
    </div>
  );
}

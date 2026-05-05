import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { getCategoryLabel, getCategoryColor } from '@/lib/utils';
import type { Strategy } from '@/types';

interface StrategyCardProps {
  strategy: Strategy;
  onClick?: () => void;
}

export function StrategyCard({ strategy, onClick }: StrategyCardProps) {
  const paramEntries = Object.entries(strategy.params).slice(0, 3);

  return (
    <Card
      className="cursor-pointer transition-shadow hover:shadow-md"
      onClick={onClick}
    >
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">{strategy.name}</CardTitle>
          <Badge className={getCategoryColor(strategy.category)}>
            {getCategoryLabel(strategy.category)}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <CardDescription className="line-clamp-3 mb-3">
          {strategy.description}
        </CardDescription>
        {paramEntries.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {paramEntries.map(([name, def]) => (
              <span
                key={name}
                className="inline-flex items-center rounded-md bg-muted px-2 py-0.5 text-xs text-muted-foreground"
              >
                {name}={String(def.default)}
              </span>
            ))}
            {Object.keys(strategy.params).length > 3 && (
              <span className="text-xs text-muted-foreground self-center">
                +{Object.keys(strategy.params).length - 3} 更多
              </span>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

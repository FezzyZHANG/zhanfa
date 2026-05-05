import { useMemo } from 'react';
import type { Watchlist } from '@/types';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';

interface WatchlistSidebarProps {
  watchlists: Watchlist[];
  selectedId: number | null;
  onSelect: (id: number) => void;
  onCreate: () => void;
  onRename: (wl: Watchlist) => void;
  onDelete: (wl: Watchlist) => void;
}

export function WatchlistSidebar({
  watchlists,
  selectedId,
  onSelect,
  onCreate,
  onRename,
  onDelete,
}: WatchlistSidebarProps) {
  const sorted = useMemo(() => {
    const defaults: Watchlist[] = [];
    const others: Watchlist[] = [];
    for (const w of watchlists) {
      if (w.name === '默认') defaults.push(w);
      else others.push(w);
    }
    return [...defaults, ...others];
  }, [watchlists]);

  return (
    <aside className="w-56 shrink-0 border-r border-border pr-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">自选分组</h2>
        <Button variant="ghost" size="sm" onClick={onCreate} title="新建分组">
          +
        </Button>
      </div>
      <nav className="space-y-0.5">
        {sorted.map((wl) => (
          <div
            key={wl.id}
            className={cn(
              'group flex items-center justify-between rounded-md px-3 py-2 text-sm cursor-pointer transition-colors',
              selectedId === wl.id
                ? 'bg-primary/10 text-primary font-medium'
                : 'hover:bg-accent text-foreground'
            )}
            onClick={() => onSelect(wl.id)}
          >
            <div className="flex items-center gap-2 min-w-0">
              <span className="truncate">{wl.name}</span>
              <span className="text-xs text-muted-foreground shrink-0">
                {wl.stock_count ?? wl.items.length}
              </span>
            </div>
            {wl.name !== '默认' && (
              <div className="hidden group-hover:flex items-center gap-0.5 ml-1 shrink-0">
                <button
                  className="p-0.5 rounded hover:bg-accent-foreground/10 text-muted-foreground text-xs"
                  onClick={(e) => { e.stopPropagation(); onRename(wl); }}
                  title="重命名"
                >
                  ✎
                </button>
                <button
                  className="p-0.5 rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive text-xs"
                  onClick={(e) => { e.stopPropagation(); onDelete(wl); }}
                  title="删除"
                >
                  ✕
                </button>
              </div>
            )}
          </div>
        ))}
      </nav>
    </aside>
  );
}

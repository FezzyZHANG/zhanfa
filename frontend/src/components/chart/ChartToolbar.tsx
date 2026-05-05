import { cn } from '@/lib/utils';
import type { Freq, IndicatorConfig } from '@/types';

const FREQ_OPTIONS: { value: Freq; label: string }[] = [
  { value: 'D', label: '日' },
  { value: 'W', label: '周' },
  { value: 'M', label: '月' },
  { value: 'Q', label: '季' },
  { value: 'Y', label: '年' },
];

const MINUTE_OPTIONS: { value: Freq; label: string }[] = [
  { value: '60min', label: '1时' },
  { value: '30min', label: '30分' },
  { value: '15min', label: '15分' },
];

const INDICATOR_OPTIONS: { type: IndicatorConfig['type']; label: string }[] = [
  { type: 'MA', label: 'MA 均线' },
  { type: 'BOLL', label: '布林带' },
  { type: 'DONCHIAN', label: '唐奇安' },
  { type: 'MACD', label: 'MACD' },
  { type: 'RSI', label: 'RSI' },
];

interface ChartToolbarProps {
  freq: Freq;
  onFreqChange: (freq: Freq) => void;
  indicators: IndicatorConfig[];
  onToggleIndicator: (type: IndicatorConfig['type']) => void;
}

export function ChartToolbar({
  freq,
  onFreqChange,
  indicators,
  onToggleIndicator,
}: ChartToolbarProps) {
  return (
    <div className="flex items-center gap-4 flex-wrap">
      <div className="flex items-center rounded-lg border border-input bg-background p-0.5">
        {FREQ_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => onFreqChange(opt.value)}
            className={cn(
              'px-3 py-1 text-xs font-medium rounded-md transition-colors',
              freq === opt.value
                ? 'bg-primary text-primary-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground',
            )}
          >
            {opt.label}
          </button>
        ))}
      </div>

      <div className="flex items-center rounded-lg border border-input bg-background p-0.5">
        {MINUTE_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => onFreqChange(opt.value)}
            className={cn(
              'px-3 py-1 text-xs font-medium rounded-md transition-colors',
              freq === opt.value
                ? 'bg-primary text-primary-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground',
            )}
          >
            {opt.label}
          </button>
        ))}
      </div>

      <div className="h-5 w-px bg-border" />

      {INDICATOR_OPTIONS.map((opt) => {
        const active = indicators.find((ind) => ind.type === opt.type)?.visible ?? false;
        return (
          <button
            key={opt.type}
            onClick={() => onToggleIndicator(opt.type)}
            className={cn(
              'px-2.5 py-1 text-xs rounded-md border transition-colors',
              active
                ? 'border-primary/50 bg-primary/10 text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground hover:bg-accent',
            )}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}

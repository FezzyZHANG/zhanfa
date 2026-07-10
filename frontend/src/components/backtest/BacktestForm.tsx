import { useState } from 'react';
import type { Strategy } from '@/types';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

interface BacktestFormProps {
  strategies: Strategy[];
  stocks: { code: string; name: string }[];
  onSubmit: (data: {
    strategy_id: number;
    stock_code: string;
    start_date: string;
    end_date: string;
    initial_capital: number;
    params: Record<string, string>;
  }) => void;
  isSubmitting: boolean;
}

export function BacktestForm({ strategies, stocks, onSubmit, isSubmitting }: BacktestFormProps) {
  const [strategyId, setStrategyId] = useState<number>(strategies[0]?.id ?? 0);
  const [selectedStock, setSelectedStock] = useState<string | null>(null);
  const [startDate, setStartDate] = useState('2023-01-01');
  const [endDate, setEndDate] = useState('2025-01-01');
  const [capital, setCapital] = useState('100000');
  const [params, setParams] = useState<Record<string, string>>({});

  const selectedStrategy = strategies.find((s) => s.id === strategyId);

  const handleSubmit = () => {
    if (!selectedStock) return;
    onSubmit({
      strategy_id: strategyId,
      stock_code: selectedStock,
      start_date: startDate,
      end_date: endDate,
      initial_capital: Number(capital),
      params,
    });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>新建回测</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Strategy */}
        <div>
          <label className="text-xs font-medium text-muted-foreground block mb-1">选择策略</label>
          <select
            value={strategyId}
            onChange={(e) => {
              setStrategyId(Number(e.target.value));
              setParams({});
            }}
            className="w-full border border-border rounded-md px-3 py-2 text-sm bg-background"
          >
            {strategies.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
        </div>

        {/* Stocks */}
        <div>
          <label className="text-xs font-medium text-muted-foreground block mb-1">选择标的</label>
          <div className="flex flex-wrap gap-1.5">
            {stocks.map((s) => (
              <button
                key={s.code}
                onClick={() => setSelectedStock(s.code)}
                className={`px-2 py-1 rounded-md text-xs font-medium transition-colors ${
                  selectedStock === s.code
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted text-muted-foreground hover:bg-muted/80'
                }`}
              >
                {s.name} ({s.code})
              </button>
            ))}
          </div>
        </div>

        {/* Date range */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs font-medium text-muted-foreground block mb-1">开始日期</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full border border-border rounded-md px-3 py-2 text-sm bg-background"
            />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground block mb-1">结束日期</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full border border-border rounded-md px-3 py-2 text-sm bg-background"
            />
          </div>
        </div>

        {/* Capital */}
        <div>
          <label className="text-xs font-medium text-muted-foreground block mb-1">初始资金</label>
          <input
            type="number"
            value={capital}
            onChange={(e) => setCapital(e.target.value)}
            className="w-full border border-border rounded-md px-3 py-2 text-sm bg-background"
          />
        </div>

        {/* Strategy params */}
        {selectedStrategy?.params && Object.keys(selectedStrategy.params).length > 0 && (
          <div>
            <label className="text-xs font-medium text-muted-foreground block mb-1">策略参数</label>
            <div className="grid grid-cols-2 gap-3">
              {Object.entries(selectedStrategy.params).map(([key, def]) => (
                <div key={key}>
                  <label className="text-xs text-muted-foreground block mb-0.5">
                    {key}
                    {def.description ? ` · ${def.description}` : ''}
                  </label>
                  <input
                    type={def.type === 'int' ? 'number' : 'text'}
                    value={params[key] ?? String(def.default)}
                    onChange={(e) => setParams((p) => ({ ...p, [key]: e.target.value }))}
                    className="w-full border border-border rounded-md px-3 py-2 text-sm bg-background"
                  />
                </div>
              ))}
            </div>
          </div>
        )}

        <Button
          className="w-full"
          disabled={!selectedStock || isSubmitting}
          onClick={handleSubmit}
        >
          {isSubmitting ? '提交中...' : '开始回测'}
        </Button>
      </CardContent>
    </Card>
  );
}

import { useState, useCallback, useRef, useEffect } from 'react';
import { useParams } from '@tanstack/react-router';
import { useStock } from '@/hooks/useStocks';
import { useChartData } from '@/hooks/useChartData';
import { KlineChart } from '@/components/chart/KlineChart';
import { ChartToolbar } from '@/components/chart/ChartToolbar';
import { ChartCrosshair } from '@/components/chart/ChartCrosshair';
import { IndicatorPane } from '@/components/chart/IndicatorPane';
import { FinancialPanel } from '@/components/financial/FinancialPanel';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Skeleton } from '@/components/ui/Skeleton';
import { formatCurrency } from '@/lib/utils';
import type { KlineData, Freq, IndicatorConfig } from '@/types';

const DEFAULT_INDICATORS: IndicatorConfig[] = [
  { type: 'MA', visible: true },
  { type: 'MACD', visible: false },
  { type: 'RSI', visible: false },
  { type: 'BOLL', visible: false },
  { type: 'DONCHIAN', visible: false },
];

type IndicatorTimeScale = {
  subscribeVisibleTimeRangeChange: (handler: (range: unknown) => void) => () => void;
  getVisibleRange: () => { from: unknown; to: unknown } | null;
  setVisibleRange: (range: { from: unknown; to: unknown }) => void;
};

export function StockDetailPage() {
  const { stockCode } = useParams({ strict: false });
  const code = stockCode ?? '';

  const [freq, setFreq] = useState<Freq>('D');
  const [indicators, setIndicators] = useState<IndicatorConfig[]>(DEFAULT_INDICATORS);
  const [crosshair, setCrosshair] = useState<{
    data: KlineData | null;
    x: number;
    y: number;
  }>({ data: null, x: 0, y: 0 });
  const [clickedDate, setClickedDate] = useState<string | null>(null);
  const [containerWidth, setContainerWidth] = useState(800);
  const [mainTimeScale, setMainTimeScale] = useState<IndicatorTimeScale | undefined>(undefined);

  const chartContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = chartContainerRef.current;
    if (!el) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setContainerWidth(entry.contentRect.width);
      }
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const { data: stock, isLoading: stockLoading } = useStock(code);
  const chartResult = useChartData(code, freq);
  const chartLoading = chartResult.isLoading;
  const handleFreqChange = useCallback((f: Freq) => setFreq(f), []);

  const handleToggleIndicator = useCallback((type: IndicatorConfig['type']) => {
    setIndicators((prev) =>
      prev.map((ind) =>
        ind.type === type ? { ...ind, visible: !ind.visible } : ind,
      ),
    );
  }, []);

  const handleCrosshairMove = useCallback(
    (data: KlineData | null, x: number, y: number) => {
      setCrosshair({ data, x, y });
    },
    [],
  );

  const handleDateClick = useCallback((date: string) => {
    setClickedDate((prev) => (prev === date ? null : date));
  }, []);

  const handleTimeScaleReady = useCallback(
    (ts: { subscribeVisibleTimeRangeChange: (handler: (range: unknown) => void) => () => void }) => {
      setMainTimeScale(ts as IndicatorTimeScale);
    },
    [],
  );

  if (stockLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-[400px]" />
      </div>
    );
  }

  if (!stock) {
    return <div className="text-center py-12 text-muted-foreground">股票不存在</div>;
  }

  const chartData = chartResult?.data ?? [];
  const indicatorsData = chartResult?.indicators;
  const showMACD = indicators.some((i) => i.type === 'MACD' && i.visible);
  const showRSI = indicators.some((i) => i.type === 'RSI' && i.visible);
  const chartDataWithTime = chartData.map((d) => ({ time: d.date, ...d }));

  return (
    <div>
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <h1 className="text-3xl font-bold tracking-tight">{stock.name}</h1>
          <span className="text-lg text-muted-foreground">{stock.code}</span>
        </div>
        <div className="flex gap-3 text-sm text-muted-foreground">
          <span>{stock.exchange} · {stock.industry}</span>
          <span>市值 {formatCurrency(stock.market_cap)}</span>
        </div>
      </div>

      <section className="mb-8">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>K 线图</CardTitle>
              <ChartToolbar
                freq={freq}
                onFreqChange={handleFreqChange}
                indicators={indicators}
                onToggleIndicator={handleToggleIndicator}
              />
            </div>
          </CardHeader>
          <CardContent>
            {chartLoading ? (
              <Skeleton className="h-[400px]" />
            ) : chartData.length > 0 ? (
              <div ref={chartContainerRef} className="relative">
                <KlineChart
                  data={chartData}
                  indicators={indicatorsData!}
                  indicatorConfigs={indicators}
                  onCrosshairMove={handleCrosshairMove}
                  onDateClick={handleDateClick}
                  onTimeScaleReady={handleTimeScaleReady}
                />
                <ChartCrosshair
                  data={crosshair.data}
                  visible={crosshair.data !== null}
                  x={crosshair.x}
                  y={crosshair.y}
                  containerWidth={containerWidth}
                />
              </div>
            ) : (
              <p className="text-center text-muted-foreground py-12">暂无K线数据</p>
            )}
          </CardContent>
        </Card>
      </section>

      {indicatorsData && showMACD && (
        <section className="mb-8">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">MACD</CardTitle>
            </CardHeader>
            <CardContent>
              <IndicatorPane
                type="MACD"
                data={chartDataWithTime}
                macd={indicatorsData.macd}
                mainTimeScale={mainTimeScale}
              />
            </CardContent>
          </Card>
        </section>
      )}

      {indicatorsData && showRSI && (
        <section className="mb-8">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">RSI (14)</CardTitle>
            </CardHeader>
            <CardContent>
              <IndicatorPane
                type="RSI"
                data={chartDataWithTime}
                rsi={indicatorsData.rsi}
                mainTimeScale={mainTimeScale}
              />
            </CardContent>
          </Card>
        </section>
      )}

      {clickedDate && (
        <section className="mb-8">
          <Card>
            <CardHeader>
              <CardTitle>K线详情 — {clickedDate}</CardTitle>
            </CardHeader>
            <CardContent>
              {(() => {
                const item = chartData.find((d) => d.date === clickedDate);
                if (!item) return <p className="text-muted-foreground">无数据</p>;
                const isUp = item.close >= item.open;
                const change = item.close - item.open;
                const changePct = item.open !== 0 ? ((change / item.open) * 100).toFixed(2) : '0.00';
                return (
                  <div className="grid grid-cols-4 gap-4 text-sm">
                    <div>
                      <span className="text-muted-foreground">开盘</span>
                      <p className="font-mono font-medium">{item.open.toFixed(2)}</p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">最高</span>
                      <p className="font-mono font-medium text-red-500">{item.high.toFixed(2)}</p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">最低</span>
                      <p className="font-mono font-medium text-green-500">{item.low.toFixed(2)}</p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">收盘</span>
                      <p className={`font-mono font-medium ${isUp ? 'text-red-500' : 'text-green-500'}`}>
                        {item.close.toFixed(2)}
                      </p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">成交量</span>
                      <p className="font-mono font-medium">{item.volume.toLocaleString('zh-CN')}</p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">涨跌</span>
                      <p className={`font-mono font-medium ${isUp ? 'text-red-500' : 'text-green-500'}`}>
                        {change >= 0 ? '+' : ''}{change.toFixed(2)} ({change >= 0 ? '+' : ''}{changePct}%)
                      </p>
                    </div>
                  </div>
                );
              })()}
            </CardContent>
          </Card>
        </section>
      )}

      <section>
        <FinancialPanel code={code} />
      </section>
    </div>
  );
}

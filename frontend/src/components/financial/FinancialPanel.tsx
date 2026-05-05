import { useState } from 'react';
import { useFinancialData } from '@/hooks/useFinancialData';
import { useStocks } from '@/hooks/useStocks';
import { useIndustryComparison } from '@/hooks/useIndustryComparison';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Skeleton } from '@/components/ui/Skeleton';
import { MetricCards } from './MetricCards';
import { RevenueProfitChart } from './RevenueProfitChart';
import { ROEChart } from './ROEChart';
import { MarginChart } from './MarginChart';
import { ValuationChart } from './ValuationChart';
import { DebtRatioChart } from './DebtRatioChart';
import { IndustryRadar } from './IndustryRadar';
import { FinancialTable } from './FinancialTable';

interface FinancialPanelProps {
  code: string;
}

export function FinancialPanel({ code }: FinancialPanelProps) {
  const [years, setYears] = useState(5);
  const { sortedData, latest, previous, yoyGrowth, recentQuarters, isLoading, error } =
    useFinancialData(code);
  const { data: stocks } = useStocks();
  const stock = stocks?.find((s) => s.code === code);
  const { data: comparison } = useIndustryComparison(stock?.industry ?? '');

  const filteredData = sortedData.filter((d) => {
    const year = parseInt(d.report_date.split('-')[0]);
    const currentYear = new Date().getFullYear();
    return year > currentYear - years;
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-24" />
        <Skeleton className="h-[350px]" />
        <Skeleton className="h-[300px]" />
      </div>
    );
  }

  if (error || !sortedData.length) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        暂无财报数据
      </div>
    );
  }

  const currentPeer = comparison?.peers.find((p) => p.code === code);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">财报分析</h2>
        <div className="flex gap-1 bg-muted rounded-lg p-0.5">
          {[3, 5, 10].map((y) => (
            <button
              key={y}
              onClick={() => setYears(y)}
              className={`px-3 py-1 text-xs rounded-md transition-colors ${
                years === y
                  ? 'bg-background text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {y}年
            </button>
          ))}
        </div>
      </div>

      <MetricCards
        latest={latest!}
        previous={previous}
        yoyGrowth={yoyGrowth}
        recentQuarters={recentQuarters}
      />

      <Card>
        <CardHeader>
          <CardTitle>营收 & 净利润</CardTitle>
        </CardHeader>
        <CardContent>
          <RevenueProfitChart data={filteredData} />
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>ROE 趋势</CardTitle>
          </CardHeader>
          <CardContent>
            <ROEChart data={filteredData} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>毛利率 / 净利率</CardTitle>
          </CardHeader>
          <CardContent>
            <MarginChart data={filteredData} />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>PE / PB 历史分位</CardTitle>
        </CardHeader>
        <CardContent>
          <ValuationChart data={filteredData} />
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>资产负债率 & 流动比率</CardTitle>
          </CardHeader>
          <CardContent>
            <DebtRatioChart data={filteredData} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>行业对比</CardTitle>
          </CardHeader>
          <CardContent>
            {comparison && comparison.peers.length > 0 ? (
              <IndustryRadar
                stockName={stock?.name ?? code}
                peers={comparison.peers}
                currentStockPeer={currentPeer}
              />
            ) : (
              <p className="text-center text-muted-foreground py-12 text-sm">
                暂无同行业对比数据
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>完整财报数据</CardTitle>
        </CardHeader>
        <CardContent>
          <FinancialTable data={sortedData} />
        </CardContent>
      </Card>
    </div>
  );
}

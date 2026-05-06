import type {
  Strategy,
  BacktestResult,
  StockInfo,
  KlineData,
  FinancialData,
  Watchlist,
  IndustryComparison,
  QuoteItem,
  WatchlistQuote,
  StockSearchResult,
  CurvePoint,
  YearlyReturn,
  MonthlyReturn,
  DataStats,
  StockDataStatus,
  RefreshResult,
} from '@/types';

function generateCurve(
  startDate: string,
  endDate: string,
  returns: number[],
  initialValue: number,
): CurvePoint[] {
  const points: CurvePoint[] = [];
  const start = new Date(startDate);
  const end = new Date(endDate);
  const current = new Date(start);
  let value = initialValue;
  let ri = 0;

  while (current <= end) {
    if (current.getDay() !== 0 && current.getDay() !== 6) {
      const dailyReturn = returns[ri % returns.length] + (Math.random() - 0.5) * 0.01;
      value *= 1 + dailyReturn;
      points.push({ date: current.toISOString().split('T')[0], value: +value.toFixed(4) });
      ri++;
    }
    current.setDate(current.getDate() + 1);
  }
  return points;
}

function generateDrawdown(equity: CurvePoint[]): CurvePoint[] {
  let peak = equity[0]?.value ?? 1;
  return equity.map((p) => {
    peak = Math.max(peak, p.value);
    return { date: p.date, value: +(p.value / peak - 1) };
  });
}

function aggregateYearly(equity: CurvePoint[]): YearlyReturn[] {
  const byYear = new Map<number, { start: number; end: number }>();
  for (const p of equity) {
    const year = new Date(p.date).getFullYear();
    if (!byYear.has(year)) byYear.set(year, { start: p.value, end: p.value });
    byYear.get(year)!.end = p.value;
  }
  return Array.from(byYear.entries())
    .map(([year, { start, end }]) => ({
      year,
      value: +(end / start - 1),
    }))
    .sort((a, b) => a.year - b.year);
}

function aggregateMonthly(equity: CurvePoint[]): MonthlyReturn[] {
  const byMonth = new Map<string, { start: number; end: number }>();
  for (const p of equity) {
    const d = new Date(p.date);
    const key = `${d.getFullYear()}-${d.getMonth()}`;
    if (!byMonth.has(key)) byMonth.set(key, { start: p.value, end: p.value });
    byMonth.get(key)!.end = p.value;
  }
  return Array.from(byMonth.entries()).map(([key, { start, end }]) => {
    const [year, month] = key.split('-').map(Number);
    return { year, month: month + 1, value: +(end / start - 1) };
  });
}

export const strategies: Strategy[] = [
  {
    id: 1,
    name: '双均线交叉策略',
    category: 'trend',
    description:
      '基于短期和长期移动平均线的交叉信号来判断趋势方向。当短期均线上穿长期均线时买入，下穿时卖出。适合趋势明显的市场环境。\n\n## 理论基础\n\n双均线系统是最经典的趋势跟踪方法之一。短期均线反映近期价格动量，长期均线反映长期趋势方向。\n\n## 适用场景\n\n- 趋势明显的单边市场\n- 中长线交易周期（日线/周线）\n\n## 风控规则\n\n- 单笔最大亏损不超过总资金的 2%\n- 连续回撤超过 15% 暂停交易',
    params: {
      fast_period: { type: 'int', default: 5, description: '快线周期' },
      slow_period: { type: 'int', default: 20, description: '慢线周期' },
    },
    code_ref: 'zhanfa.strategies.trend.SMACross',
    backtest_count: 1,
    created_at: '2025-01-15T08:00:00Z',
    updated_at: '2025-04-20T10:30:00Z',
  },
  {
    id: 2,
    name: '海龟交易法则',
    category: 'trend',
    description:
      '经典的趋势跟踪策略，基于唐奇安通道突破。当价格突破N日高点时入场，跌破N日低点时离场，配合ATR动态仓位管理。\n\n## 理论基础\n\nRichard Dennis 和 William Eckhardt 的海龟实验证明了趋势跟踪可以被教授。该策略使用唐奇安通道作为入场和离场信号。\n\n## 适用场景\n\n- 期货和外汇等高流动性市场\n- 日线交易周期\n\n## 风控规则\n\n- ATR 倍数动态止损\n- 单品种最大仓位不超过总资金的 4%',
    params: {
      entry_period: { type: 'int', default: 20, description: '入场通道周期' },
      exit_period: { type: 'int', default: 10, description: '离场通道周期' },
      atr_period: { type: 'int', default: 20, description: 'ATR 计算周期' },
      atr_mult: { type: 'float', default: 2.0, description: '止损 ATR 倍数' },
    },
    code_ref: 'zhanfa.strategies.trend.Turtle',
    backtest_count: 0,
    created_at: '2025-02-01T08:00:00Z',
    updated_at: '2025-04-10T14:00:00Z',
  },
  {
    id: 3,
    name: 'RSI 超买超卖策略',
    category: 'momentum',
    description:
      '利用相对强弱指标识别超买超卖区域。当RSI低于30时视为超卖买入信号，高于70时视为超买卖出信号。\n\n## 理论基础\n\nRSI 由 J. Welles Wilder 提出，衡量价格变动的速度和幅度。超买超卖区域代表价格可能反转的位置。\n\n## 适用场景\n\n- 震荡市场\n- 短线交易\n\n## 风控规则\n\n- 结合趋势过滤，避免逆势交易\n- 止损设为入场价的 2 ATR',
    params: {
      rsi_period: { type: 'int', default: 14, description: 'RSI 计算周期' },
      oversold: { type: 'int', default: 30, description: '超卖阈值' },
      overbought: { type: 'int', default: 70, description: '超买阈值' },
    },
    code_ref: 'zhanfa.strategies.momentum.RSIStrategy',
    backtest_count: 1,
    created_at: '2025-01-20T08:00:00Z',
    updated_at: '2025-03-15T09:00:00Z',
  },
  {
    id: 4,
    name: 'MACD 金叉死叉策略',
    category: 'momentum',
    description:
      '基于MACD指标的DIF线与DEA线交叉信号。金叉（DIF上穿DEA）做多，死叉（DIF下穿DEA）平多或做空。\n\n## 理论基础\n\nMACD 由 Gerald Appel 提出，通过快慢线交叉和柱状图变化捕捉趋势转折点。\n\n## 适用场景\n\n- 趋势转折点捕捉\n- 中短线交易\n\n## 风控规则\n\n- DIF 在零轴上方只做多，下方只做空\n- 止损设为信号 K 线低点',
    params: {
      fast: { type: 'int', default: 12, description: '快线 EMA 周期' },
      slow: { type: 'int', default: 26, description: '慢线 EMA 周期' },
      signal: { type: 'int', default: 9, description: '信号线 EMA 周期' },
    },
    code_ref: 'zhanfa.strategies.momentum.MACDStrategy',
    backtest_count: 0,
    created_at: '2025-02-10T08:00:00Z',
    updated_at: '2025-04-18T11:00:00Z',
  },
  {
    id: 5,
    name: '低市盈率价值策略',
    category: 'fundamental',
    description:
      '筛选市盈率低于行业平均水平且ROE高于15%的股票，按月调仓，持有具有安全边际的价值标的。\n\n## 理论基础\n\n基于 Benjamin Graham 的价值投资理念，寻找价格低于内在价值的公司。低 PE 代表市场估值较低，高 ROE 代表公司盈利能力较强。\n\n## 适用场景\n\n- 长期投资（月线调仓）\n- 熊市防御\n\n## 风控规则\n\n- 单只股票最大仓位 10%\n- 行业集中度不超过 30%',
    params: {
      max_pe: { type: 'float', default: 15, description: '最大市盈率' },
      min_roe: { type: 'float', default: 0.15, description: '最小 ROE' },
      rebalance_freq: { type: 'str', default: 'monthly', description: '调仓频率' },
    },
    code_ref: 'zhanfa.strategies.fundamental.LowPEStrategy',
    backtest_count: 0,
    created_at: '2025-02-15T08:00:00Z',
    updated_at: '2025-04-22T16:00:00Z',
  },
  {
    id: 6,
    name: '彼得·林奇 PEG 策略',
    category: 'fundamental',
    description:
      '使用PEG指标（市盈率/盈利增长率）寻找被低估的成长股。PEG < 0.5 被视为极度低估，PEG < 1 为合理低估。\n\n## 理论基础\n\nPeter Lynch 提出的 PEG 指标综合考虑了估值和成长性，避免了单纯低 PE 策略可能陷入的价值陷阱。\n\n## 适用场景\n\n- 成长股投资\n- 中长线持有\n\n## 风控规则\n\n- PEG > 2 强制平仓\n- 盈利增长率连续两季下滑则剔除',
    params: {
      max_peg: { type: 'float', default: 1, description: '最大 PEG 值' },
      min_growth: { type: 'float', default: 0.1, description: '最小盈利增长率' },
      max_pe: { type: 'float', default: 30, description: '最大市盈率' },
    },
    code_ref: 'zhanfa.strategies.fundamental.PEGStrategy',
    backtest_count: 0,
    created_at: '2025-03-01T08:00:00Z',
    updated_at: '2025-04-25T08:00:00Z',
  },
  {
    id: 7,
    name: '趋势+基本面共振策略',
    category: 'composite',
    description:
      '结合趋势跟踪和基本面分析：先通过均线系统确认上升趋势，再筛选低估值高成长个股，形成多维度验证的选股体系。\n\n## 理论基础\n\n多维度验证可以显著降低虚假信号。趋势确认保证市场方向，基本面筛选保证标的质量。\n\n## 适用场景\n\n- 牛市中期\n- 行业轮动\n\n## 风控规则\n\n- 趋势转空则全部平仓\n- 单次调仓不超过 20 只股票',
    params: {
      ma_period: { type: 'int', default: 60, description: '均线周期' },
      max_pe: { type: 'float', default: 20, description: '最大市盈率' },
      min_roe: { type: 'float', default: 0.12, description: '最小 ROE' },
    },
    code_ref: 'zhanfa.strategies.composite.TrendFundamental',
    backtest_count: 0,
    created_at: '2025-03-15T08:00:00Z',
    updated_at: '2025-05-01T09:00:00Z',
  },
  {
    id: 8,
    name: '动量+低波多因子策略',
    category: 'composite',
    description:
      '多因子打分模型，综合动量因子、波动率因子、质量因子和规模因子，每月选取得分最高的前20只股票等权配置。\n\n## 理论基础\n\nFama-French 多因子模型的扩展应用。动量因子捕捉趋势，低波因子控制回撤，质量因子确保基本面，规模因子分散风险。\n\n## 适用场景\n\n- 量化组合管理\n- 月度调仓\n\n## 风控规则\n\n- 单因子暴露不超过 40%\n- 最大换手率限制 50%',
    params: {
      top_n: { type: 'int', default: 20, description: '持仓数量' },
      factors: { type: 'list', default: ['momentum', 'volatility', 'quality', 'size'], description: '因子列表' },
    },
    code_ref: 'zhanfa.strategies.composite.MomentumLowVol',
    backtest_count: 0,
    created_at: '2025-03-20T08:00:00Z',
    updated_at: '2025-05-03T10:00:00Z',
  },
];

export const backtestResults: BacktestResult[] = (() => {
  const equity1 = generateCurve('2023-01-01', '2025-01-01', [0.005, 0.008, -0.003, -0.006, 0.012, 0.004, -0.002], 1);
  const equity2 = generateCurve('2023-01-01', '2025-01-01', [0.003, -0.005, 0.007, 0.004, -0.008, 0.006, 0.002], 1);
  const bench1 = generateCurve('2023-01-01', '2025-01-01', [0.002, 0.003, -0.001, 0.001, 0.004, -0.002, 0.001], 1);

  return [
    {
      id: '1',
      strategy_id: 1,
      strategy_name: '双均线交叉策略',
      stock_codes: ['600519', '000858'],
      params: { fast_period: 5, slow_period: 20 },
      start_date: '2023-01-01',
      end_date: '2025-01-01',
      metrics: {
        total_return: 0.324,
        ann_return: 0.151,
        ann_volatility: 0.185,
        sharpe: 0.89,
        sortino: 1.35,
        max_drawdown: -0.18,
        calmar: 0.84,
        win_rate: 0.42,
        years: 2.0,
        benchmark_return: 0.105,
        excess_return: 0.219,
        ann_excess: 0.104,
        profit_factor: 1.8,
        total_trades: 47,
      },
      equity_curve: equity1,
      drawdown_curve: generateDrawdown(equity1),
      benchmark_curve: bench1,
      yearly_returns: aggregateYearly(equity1),
      monthly_returns: aggregateMonthly(equity1),
      trades: [
        { date: '2023-02-15', action: 'buy', price: 1850.0, quantity: 100 },
        { date: '2023-05-20', action: 'sell', price: 1920.0, quantity: 100, pnl: 7000 },
        { date: '2023-07-10', action: 'buy', price: 1780.0, quantity: 100 },
        { date: '2023-09-28', action: 'sell', price: 1860.0, quantity: 100, pnl: 8000 },
        { date: '2024-01-05', action: 'buy', price: 1650.0, quantity: 200 },
        { date: '2024-04-12', action: 'sell', price: 1720.0, quantity: 200, pnl: 14000 },
      ],
      status: 'done',
      created_at: '2025-04-10T08:00:00Z',
    },
    {
      id: '2',
      strategy_id: 3,
      strategy_name: 'RSI 超买超卖策略',
      stock_codes: ['300750'],
      params: { rsi_period: 14, oversold: 30, overbought: 70 },
      start_date: '2023-01-01',
      end_date: '2025-01-01',
      metrics: {
        total_return: 0.186,
        ann_return: 0.089,
        ann_volatility: 0.22,
        sharpe: 0.52,
        sortino: 0.78,
        max_drawdown: -0.25,
        calmar: 0.36,
        win_rate: 0.38,
        years: 2.0,
        profit_factor: 1.35,
        total_trades: 35,
      },
      equity_curve: equity2,
      drawdown_curve: generateDrawdown(equity2),
      benchmark_curve: bench1,
      yearly_returns: aggregateYearly(equity2),
      monthly_returns: aggregateMonthly(equity2),
      trades: [
        { date: '2023-03-08', action: 'buy', price: 380.0, quantity: 500 },
        { date: '2023-06-15', action: 'sell', price: 410.0, quantity: 500, pnl: 15000 },
        { date: '2023-10-20', action: 'buy', price: 350.0, quantity: 500 },
        { date: '2024-02-28', action: 'sell', price: 375.0, quantity: 500, pnl: 12500 },
      ],
      status: 'done',
      created_at: '2025-04-12T08:00:00Z',
    },
  ];
})();

export const stocks: StockInfo[] = [
  {
    code: '600519',
    name: '贵州茅台',
    exchange: 'SH',
    industry: '白酒',
    market_cap: 2_200_000_000_000,
    listed_date: '2001-08-27',
  },
  {
    code: '000858',
    name: '五粮液',
    exchange: 'SZ',
    industry: '白酒',
    market_cap: 620_000_000_000,
    listed_date: '1998-04-27',
  },
  {
    code: '300750',
    name: '宁德时代',
    exchange: 'SZ',
    industry: '电池',
    market_cap: 950_000_000_000,
    listed_date: '2018-06-11',
  },
  {
    code: '600036',
    name: '招商银行',
    exchange: 'SH',
    industry: '银行',
    market_cap: 880_000_000_000,
    listed_date: '2002-04-09',
  },
];

const generateKlineData = (code: string): KlineData[] => {
  const data: KlineData[] = [];
  const basePrice = code === '600519' ? 1650 : code === '300750' ? 210 : 25;
  let price = basePrice;
  const startDate = new Date('2024-01-01');

  for (let i = 0; i < 250; i++) {
    const date = new Date(startDate);
    date.setDate(date.getDate() + i);
    if (date.getDay() === 0 || date.getDay() === 6) continue;

    const change = (Math.random() - 0.5) * basePrice * 0.04;
    const open = price;
    const close = price + change;
    const high = Math.max(open, close) + Math.random() * basePrice * 0.015;
    const low = Math.min(open, close) - Math.random() * basePrice * 0.015;
    const volume = Math.floor(Math.random() * 10_000_000 + 2_000_000);

    data.push({
      date: date.toISOString().split('T')[0],
      open: +open.toFixed(2),
      high: +high.toFixed(2),
      low: +low.toFixed(2),
      close: +close.toFixed(2),
      volume,
    });
    price = close;
  }
  return data;
};

const klineCache: Record<string, KlineData[]> = {};

export function getKlineData(code: string, start?: string, end?: string): KlineData[] {
  if (!klineCache[code]) {
    klineCache[code] = generateKlineData(code);
  }
  let data = klineCache[code];
  if (start) data = data.filter((d) => d.date >= start);
  if (end) data = data.filter((d) => d.date <= end);
  return data;
}

export const financialData: Record<string, FinancialData[]> = {
  '600519': [
    { report_date: '2024-12-31', net_profit: 74_700_000_000, revenue: 148_000_000_000, eps: 59.49, roe: 0.294, debt_ratio: 0.192, current_ratio: 4.28, dividend_yield: 0.019, pe: 27.8, pb: 8.2, gross_margin: 0.918, net_margin: 0.505 },
    { report_date: '2023-12-31', net_profit: 65_300_000_000, revenue: 130_000_000_000, eps: 52.05, roe: 0.312, debt_ratio: 0.185, current_ratio: 4.51, dividend_yield: 0.018, pe: 30.2, pb: 9.1, gross_margin: 0.920, net_margin: 0.502 },
    { report_date: '2022-12-31', net_profit: 58_200_000_000, revenue: 117_000_000_000, eps: 46.35, roe: 0.328, debt_ratio: 0.179, current_ratio: 5.02, dividend_yield: 0.017, pe: 32.5, pb: 10.3, gross_margin: 0.919, net_margin: 0.497 },
    { report_date: '2021-12-31', net_profit: 52_100_000_000, revenue: 109_000_000_000, eps: 41.50, roe: 0.315, debt_ratio: 0.181, current_ratio: 4.90, dividend_yield: 0.014, pe: 35.1, pb: 11.0, gross_margin: 0.916, net_margin: 0.478 },
    { report_date: '2020-12-31', net_profit: 46_700_000_000, revenue: 95_000_000_000, eps: 37.17, roe: 0.307, debt_ratio: 0.178, current_ratio: 5.10, dividend_yield: 0.013, pe: 38.5, pb: 12.5, gross_margin: 0.914, net_margin: 0.491 },
  ],
  '000858': [
    { report_date: '2024-12-31', net_profit: 24_800_000_000, revenue: 67_000_000_000, eps: 6.39, roe: 0.238, debt_ratio: 0.201, current_ratio: 3.95, dividend_yield: 0.021, pe: 22.5, pb: 5.4, gross_margin: 0.752, net_margin: 0.370 },
    { report_date: '2023-12-31', net_profit: 22_100_000_000, revenue: 60_000_000_000, eps: 5.70, roe: 0.251, debt_ratio: 0.195, current_ratio: 4.12, dividend_yield: 0.020, pe: 24.8, pb: 6.1, gross_margin: 0.748, net_margin: 0.368 },
    { report_date: '2022-12-31', net_profit: 19_800_000_000, revenue: 53_000_000_000, eps: 5.10, roe: 0.263, debt_ratio: 0.188, current_ratio: 4.35, dividend_yield: 0.018, pe: 27.0, pb: 6.8, gross_margin: 0.751, net_margin: 0.374 },
    { report_date: '2021-12-31', net_profit: 17_500_000_000, revenue: 47_000_000_000, eps: 4.51, roe: 0.270, debt_ratio: 0.192, current_ratio: 4.28, dividend_yield: 0.017, pe: 28.5, pb: 7.2, gross_margin: 0.745, net_margin: 0.372 },
    { report_date: '2020-12-31', net_profit: 15_200_000_000, revenue: 40_000_000_000, eps: 3.92, roe: 0.258, debt_ratio: 0.190, current_ratio: 4.40, dividend_yield: 0.016, pe: 30.0, pb: 7.8, gross_margin: 0.740, net_margin: 0.380 },
  ],
  '300750': [
    { report_date: '2024-12-31', net_profit: 44_100_000_000, revenue: 400_900_000_000, eps: 10.02, roe: 0.224, debt_ratio: 0.423, current_ratio: 1.85, dividend_yield: 0.012, pe: 21.0, pb: 4.7, gross_margin: 0.228, net_margin: 0.110 },
    { report_date: '2023-12-31', net_profit: 38_700_000_000, revenue: 362_000_000_000, eps: 8.81, roe: 0.248, debt_ratio: 0.411, current_ratio: 1.92, dividend_yield: 0.011, pe: 23.8, pb: 5.3, gross_margin: 0.235, net_margin: 0.107 },
    { report_date: '2022-12-31', net_profit: 30_100_000_000, revenue: 280_000_000_000, eps: 6.85, roe: 0.268, debt_ratio: 0.398, current_ratio: 2.05, dividend_yield: 0.009, pe: 28.5, pb: 6.8, gross_margin: 0.251, net_margin: 0.108 },
    { report_date: '2021-12-31', net_profit: 18_200_000_000, revenue: 155_000_000_000, eps: 4.15, roe: 0.253, debt_ratio: 0.425, current_ratio: 1.78, dividend_yield: 0.007, pe: 45.0, pb: 10.2, gross_margin: 0.262, net_margin: 0.117 },
    { report_date: '2020-12-31', net_profit: 5_800_000_000, revenue: 58_000_000_000, eps: 1.33, roe: 0.113, debt_ratio: 0.452, current_ratio: 1.65, dividend_yield: 0.005, pe: 75.0, pb: 15.5, gross_margin: 0.275, net_margin: 0.100 },
  ],
  '600036': [
    { report_date: '2024-12-31', net_profit: 146_600_000_000, revenue: 330_000_000_000, eps: 5.81, roe: 0.148, debt_ratio: 0.912, current_ratio: 1.25, dividend_yield: 0.052, pe: 6.8, pb: 0.95, gross_margin: 0.485, net_margin: 0.444 },
    { report_date: '2023-12-31', net_profit: 138_000_000_000, revenue: 310_000_000_000, eps: 5.47, roe: 0.155, debt_ratio: 0.913, current_ratio: 1.22, dividend_yield: 0.050, pe: 7.2, pb: 1.02, gross_margin: 0.480, net_margin: 0.445 },
    { report_date: '2022-12-31', net_profit: 128_000_000_000, revenue: 285_000_000_000, eps: 5.07, roe: 0.162, debt_ratio: 0.915, current_ratio: 1.20, dividend_yield: 0.048, pe: 7.8, pb: 1.12, gross_margin: 0.478, net_margin: 0.449 },
    { report_date: '2021-12-31', net_profit: 112_000_000_000, revenue: 255_000_000_000, eps: 4.44, roe: 0.168, debt_ratio: 0.916, current_ratio: 1.18, dividend_yield: 0.045, pe: 8.5, pb: 1.25, gross_margin: 0.482, net_margin: 0.439 },
    { report_date: '2020-12-31', net_profit: 98_000_000_000, revenue: 228_000_000_000, eps: 3.88, roe: 0.158, debt_ratio: 0.917, current_ratio: 1.15, dividend_yield: 0.042, pe: 9.2, pb: 1.38, gross_margin: 0.475, net_margin: 0.430 },
  ],
};

export const industryComparison: Record<string, IndustryComparison> = {
  '白酒': {
    industry: '白酒',
    peers: [
      { code: '600519', name: '贵州茅台', roe: 0.294, gross_margin: 0.918, debt_ratio: 0.192, revenue_growth: 0.138, net_profit_growth: 0.144 },
      { code: '000858', name: '五粮液', roe: 0.238, gross_margin: 0.752, debt_ratio: 0.201, revenue_growth: 0.117, net_profit_growth: 0.122 },
    ],
  },
  '电池': {
    industry: '电池',
    peers: [
      { code: '300750', name: '宁德时代', roe: 0.224, gross_margin: 0.228, debt_ratio: 0.423, revenue_growth: 0.107, net_profit_growth: 0.140 },
    ],
  },
  '银行': {
    industry: '银行',
    peers: [
      { code: '600036', name: '招商银行', roe: 0.148, gross_margin: 0.485, debt_ratio: 0.912, revenue_growth: 0.065, net_profit_growth: 0.062 },
    ],
  },
};

export const watchlists: Watchlist[] = [
  {
    id: 1,
    name: '默认',
    stock_count: 0,
    items: [],
    created_at: '2025-01-01T08:00:00Z',
  },
  {
    id: 2,
    name: '白酒板块',
    stock_count: 2,
    items: [
      { code: '600519', name: '贵州茅台', added_at: '2025-01-10T08:00:00Z', notes: '海龟策略入选' },
      { code: '000858', name: '五粮液', added_at: '2025-01-10T08:00:00Z', notes: '' },
    ],
    created_at: '2025-01-10T08:00:00Z',
  },
  {
    id: 3,
    name: '新能源',
    stock_count: 1,
    items: [
      { code: '300750', name: '宁德时代', added_at: '2025-02-15T08:00:00Z', notes: '' },
    ],
    created_at: '2025-02-15T08:00:00Z',
  },
];

const _defaultDataStatus = {
  has_daily: true,
  has_financial: true,
  daily_start: '2020-01-02',
  daily_end: '2026-05-04',
  financial_periods: 20,
};

export function getWatchlistQuotes(_wlId: number): WatchlistQuote {
  const quotes: Record<number, QuoteItem[]> = {
    2: [
      { code: '600519', name: '贵州茅台', latest_price: 1685.50, change_pct: 0.0215, pe: 28.3, pb: 8.4, dividend_yield: 0.0185, notes: '海龟策略入选', data_status: _defaultDataStatus, data_freshness: 'cached' },
      { code: '000858', name: '五粮液', latest_price: 142.30, change_pct: -0.0082, pe: 22.2, pb: 5.2, dividend_yield: 0.0212, notes: '', data_status: _defaultDataStatus, data_freshness: 'cached' },
    ],
    3: [
      { code: '300750', name: '宁德时代', latest_price: 205.80, change_pct: 0.0331, pe: 20.5, pb: 4.6, dividend_yield: 0.0122, notes: '', data_status: _defaultDataStatus, data_freshness: 'cached' },
    ],
  };
  const wl = watchlists.find((w) => w.id === _wlId);
  return {
    id: _wlId,
    name: wl?.name || '',
    items: quotes[_wlId] || [],
  };
}

const _mockStockList: StockSearchResult[] = [
  { code: '600519', name: '贵州茅台' },
  { code: '000858', name: '五粮液' },
  { code: '300750', name: '宁德时代' },
  { code: '600036', name: '招商银行' },
  { code: '000001', name: '平安银行' },
  { code: '600900', name: '长江电力' },
  { code: '002415', name: '海康威视' },
  { code: '600276', name: '恒瑞医药' },
  { code: '000333', name: '美的集团' },
  { code: '600585', name: '海螺水泥' },
];

export function searchStocks(q: string): StockSearchResult[] {
  const kw = q.toLowerCase();
  return _mockStockList.filter(
    (s) => s.code.includes(kw) || s.name.toLowerCase().includes(kw)
  );
}

// ── Data Management ──────────────────────────────

export const dataStats: DataStats = {
  cache: {
    stock_count: 4523,
    total_rows: 12_580_000,
    storage_bytes: 487_000_000,
    date_range_start: '2010-01-04',
    date_range_end: '2026-05-04',
    freq_stats: {
      daily: 4523,
      financial: 3200,
      index_daily: 5,
      meta: 3,
    },
    last_refreshed_at: '2026-05-04T15:30:00Z',
  },
  database: {
    stock_count: 5000,
    financial_count: 28500,
    watchlist_count: 3,
    strategy_count: 8,
    backtest_count: 15,
  },
};

export const stockDataStatusMap: Record<string, StockDataStatus> = {
  '600519': {
    code: '600519',
    name: '贵州茅台',
    has_daily: true,
    daily_start: '2010-01-04',
    daily_end: '2026-05-04',
    daily_rows: 3976,
    daily_cached_at: '2026-05-04T15:30:00Z',
    has_financial: true,
    financial_start: '2010-03-31',
    financial_end: '2025-12-31',
    financial_rows: 64,
    financial_cached_at: '2026-05-04T15:30:00Z',
    in_watchlist: ['白酒板块'],
  },
  '000858': {
    code: '000858',
    name: '五粮液',
    has_daily: true,
    daily_start: '2010-01-04',
    daily_end: '2026-05-04',
    daily_rows: 3978,
    daily_cached_at: '2026-05-04T15:30:00Z',
    has_financial: true,
    financial_start: '2010-03-31',
    financial_end: '2025-12-31',
    financial_rows: 64,
    financial_cached_at: '2026-05-04T15:30:00Z',
    in_watchlist: ['白酒板块'],
  },
  '300750': {
    code: '300750',
    name: '宁德时代',
    has_daily: true,
    daily_start: '2018-06-11',
    daily_end: '2026-05-04',
    daily_rows: 1940,
    daily_cached_at: '2026-05-04T15:30:00Z',
    has_financial: true,
    financial_start: '2018-06-30',
    financial_end: '2025-12-31',
    financial_rows: 30,
    financial_cached_at: '2026-05-04T15:30:00Z',
    in_watchlist: ['新能源'],
  },
  '600036': {
    code: '600036',
    name: '招商银行',
    has_daily: true,
    daily_start: '2010-01-04',
    daily_end: '2026-05-04',
    daily_rows: 3980,
    daily_cached_at: '2026-05-04T15:30:00Z',
    has_financial: true,
    financial_start: '2010-03-31',
    financial_end: '2025-12-31',
    financial_rows: 64,
    financial_cached_at: '2026-05-04T15:30:00Z',
    in_watchlist: [],
  },
  '000001': {
    code: '000001',
    name: '平安银行',
    has_daily: true,
    daily_start: '2010-01-04',
    daily_end: '2026-05-04',
    daily_rows: 3981,
    daily_cached_at: '2026-05-04T15:30:00Z',
    has_financial: true,
    financial_start: '2010-03-31',
    financial_end: '2025-12-31',
    financial_rows: 64,
    financial_cached_at: '2026-05-04T15:30:00Z',
    in_watchlist: [],
  },
};

export function mockRefreshData(codes?: string[] | null, force?: boolean): RefreshResult {
  const list = codes || ['600519', '000858', '300750', '600036', '000001'];
  return {
    updated: force ? list.length : Math.max(1, list.length - 1),
    failed: force ? 0 : 1,
    new_discovered: force ? 2 : 0,
    errors: force
      ? []
      : [{ code: list[list.length - 1], error: '模拟网络错误' }],
  };
}

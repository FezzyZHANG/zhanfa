# TICKET-008: 回测结果可视化

**优先级:** P2 - 中
**状态:** ✅ 已完成
**依赖:** 002, 004
**预计工时:** 2d

## 需求描述

在前端展示回测结果的绩效指标、净值曲线、回撤区间和交易记录，替代目前的 Markdown 纯文本报告。

## 功能清单

### 回测结果仪表盘

顶部指标卡片（参考 [backtest/metrics.py](../../src/zhanfa/backtest/metrics.py) 的输出）：

| 指标         | 格式     |
| ------------ | -------- |
| 总收益率     | +35.2%   |
| 年化收益率   | 12.8%    |
| 年化波动率   | 18.5%    |
| 夏普比率     | 1.20     |
| 索提诺比率   | 1.85     |
| 最大回撤     | -15.3%   |
| 卡玛比率     | 0.84     |
| 胜率         | 52.3%    |

### 图表

- [x] 净值曲线 (cumulative returns) — 主图，含基准对比线
- [x] 回撤曲线 (drawdown) — 副图，标记最大回撤区间
- [x] 年度收益柱状图 — 按年汇总收益率
- [x] 月度收益热力图 — 日历热力图

### 交易记录

- [x] 交易列表表格：日期 | 方向(买/卖) | 价格 | 数量 | 盈亏
- [x] 分页 & 筛选（按日期范围）
- [x] 导出为 CSV

### 回测对比

- [x] 多策略同标的对比：净值曲线叠加、指标表格并列
- [ ] 策略选股回测：多股票分别回测，横向对比（待后端 API 支持）

## 技术方案

- 净值曲线和回撤曲线用 TradingView Lightweight Charts（与 K 线图一致）
- 热力图和柱状图用 ECharts
- 回测任务异步执行（POST → task_id → poll GET）

```typescript
interface BacktestResult {
  id: number;
  strategy: { id: number; name: string };
  stock_codes: string[];
  params: Record<string, unknown>;
  start_date: string;
  end_date: string;
  metrics: BacktestMetrics;
  equity_curve: { date: string; value: number }[];   // 净值序列
  drawdown_curve: { date: string; value: number }[];  // 回撤序列
  trades: Trade[];
  benchmark_curve?: { date: string; value: number }[]; // 基准净值
  status: 'done';
  created_at: string;
}
```

## 组件拆分

```
components/backtest/
├── BacktestPage.tsx         # 回测表单 + 历史列表
├── BacktestForm.tsx         # 策略选择 + 参数填写 + 日期范围
├── BacktestDashboard.tsx    # 结果仪表盘
├── BacktestMetrics.tsx      # 顶部指标卡片
├── EquityCurve.tsx          # 净值曲线
├── DrawdownCurve.tsx        # 回撤曲线
├── YearlyReturns.tsx        # 年度收益柱状图
├── MonthlyHeatmap.tsx       # 月度收益热力图
├── TradeTable.tsx           # 交易记录表格
├── CompareView.tsx          # 多策略对比
└── useBacktest.ts           # 回测提交 & 轮询 hook
```

## 验收标准

- [x] 提交回测 → 显示进度 → 完成后自动展示结果
- [x] 净值曲线与回撤区间标记正确
- [x] 指标卡片数值与 CLI 回测输出一致（字段对齐 metrics.py）
- [x] 交易记录表格包含所有买卖点
- [x] 多策略对比净值叠加不混乱（颜色区分 + 图例）
- [x] 回测历史列表支持查看和删除

## 备注

- 回测耗时长（全 A 股 SMA 交叉约 1-3 分钟），必须异步。前端提交后用 `useQuery` 轮询状态（每 2 秒查一次）。
- 净值曲线数据量 = 回测天数，通常几千个点，JSON 传输没问题。
- 月度热力图用 ECharts 的 heatmap 类型，类似 GitHub 贡献图风格。

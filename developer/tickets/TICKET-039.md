# TICKET-039: lightweight-charts v5 API 迁移

**优先级:** P1 - 高
**状态:** ✅ 已完成
**依赖:** TICKET-028, TICKET-031
**预计工时:** 1d

## 需求描述

当前前端使用 `lightweight-charts@5.2.0`，但多个图表组件仍调用旧 API，例如 `addLineSeries()`、`addCandlestickSeries()`、`addHistogramSeries()`、`addAreaSeries()`。需要迁移到 v5 的 `addSeries(...)` API，并修正时间范围同步类型。

## 范围边界

**负责文件优先级:**

- `frontend/src/components/chart/KlineChart.tsx`
- `frontend/src/components/chart/IndicatorPane.tsx`
- `frontend/src/components/backtest/EquityCurve.tsx`
- `frontend/src/components/backtest/DrawdownCurve.tsx`
- `frontend/src/components/watchlist/WatchlistCards.tsx`
- 必要时可调整图表相关局部 helper/types

避免修改 API client、页面路由和非图表业务组件；这些由 `TICKET-038` / `TICKET-040` 负责。

## 已知错误

- `IChartApi` 不存在 `addCandlestickSeries`
- `IChartApi` 不存在 `addLineSeries`
- `IChartApi` 不存在 `addHistogramSeries`
- `IChartApi` 不存在 `addAreaSeries`
- `subscribeVisibleTimeRangeChange()` 返回值和 handler 类型与当前代码假设不一致

## 任务清单

- [x] 使用 v5 series constructors 替换旧的 add*Series 调用
- [x] 修正 K 线、成交量、均线、MACD、RSI、BOLL、DONCHIAN 的 series 类型
- [x] 修正回测净值曲线和回撤曲线
- [x] 修正图表间可见时间范围同步类型
- [x] 保持现有视觉效果和交互行为

## 验收标准

- [x] `cd frontend && npx tsc -p tsconfig.app.json --noEmit` 不再出现 lightweight-charts API 错误
- [x] `cd frontend && npm run test` 通过
- [x] 图表组件运行时不报错（已通过构建与组件测试覆盖，未手动浏览器验证）

## 备注

- 从已取消的 `TICKET-031` 拆分
- 可参考 lightweight-charts v5 文档中的 `chart.addSeries(LineSeries, options)` 用法
- 完成时间: 2026-05-05
- 验证结果: `npm run build` 与 `npm run test` 通过

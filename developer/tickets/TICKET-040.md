# TICKET-040: 前端页面/组件严格类型清理

**优先级:** P1 - 高
**状态:** ✅ 已完成
**依赖:** TICKET-031
**预计工时:** 0.5d

## 需求描述

清理前端页面和普通组件中的严格 TypeScript 错误，补齐缺失类型、移除未使用变量、修正路径和数据结构假设，使构建接近全绿。

## 范围边界

**负责文件优先级:**

- `frontend/src/pages/**/*.tsx`
- `frontend/src/components/data/StockDataTable.tsx`
- `frontend/src/components/financial/IndustryRadar.tsx`
- `frontend/src/components/financial/MetricCards.tsx`
- `frontend/src/components/backtest/CompareView.tsx`
- `frontend/src/components/backtest/MonthlyHeatmap.tsx`
- `frontend/src/components/chart/ChartToolbar.tsx`
- `frontend/src/hooks/useChartData.ts`
- 测试文件中的未使用 import 清理

避免修改 lightweight-charts 旧 API 调用主体；这些由 `TICKET-039` 负责。避免修改 API client 核心映射；这些由 `TICKET-038` 负责。

## 已知错误

- `CompareView` 将 `string | number` id 传给只接受 number 的格式化函数
- `MonthlyHeatmap`、`IndustryRadar`、`MetricCards`、`ChartToolbar` 等存在未使用变量/import
- `StockDataTable` 排序值为 `unknown`
- `/stock/$code` 与实际 router path `/stock/$stockCode` 不一致
- `useChartData` 中 `key` 可能未赋值
- 页面中部分 hook 返回值类型被推断成 `{}` 或 `KlineData[]` 后错误访问

## 任务清单

- [x] 清理普通页面/组件中的未使用变量和 import
- [x] 修正 `StockDataTable` 排序类型与 stock route path
- [x] 修正 `useChartData` 聚合逻辑中的未赋值变量
- [x] 修正页面使用 hook 数据时的空值和类型收窄
- [x] 不改变现有 UI 行为

## 验收标准

- [x] `cd frontend && npx tsc -p tsconfig.app.json --noEmit` 不再出现本工单范围内错误
- [x] `cd frontend && npm run test` 通过

## 备注

- 从已取消的 `TICKET-031` 拆分
- 与 `TICKET-038`、`TICKET-039` 并行推进，注意避免写入同一文件

## Worker E Status

- Status: completed (2026-05-05)
- Verification: `cd frontend && npm run build` and `cd frontend && npm run test` pass.

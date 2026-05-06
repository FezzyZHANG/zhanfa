# TICKET-031: 前端生产构建失败

**优先级:** P1 - 高
**状态:** ❌ 取消
**依赖:** TICKET-028, TICKET-022
**预计工时:** 1d

## 取消说明

该工单覆盖面过大，已拆解为 3 个更可执行的 debug 工单：

- `TICKET-038`: 前端 TypeScript 配置与核心类型修复
- `TICKET-039`: lightweight-charts v5 API 迁移
- `TICKET-040`: 前端页面/组件严格类型清理

后续修复以上述 3 个工单为准。

## 症状

`cd frontend && npm run build` 当前失败。

第一层失败来自 TypeScript 6 对 `baseUrl` 的废弃检查：

```text
tsconfig.app.json(25,5): error TS5101: Option 'baseUrl' is deprecated
```

绕过该检查后，仍有多处真实类型/API 错误，包括：

- `frontend/src/api/client.ts` 访问不存在的 `strategy_id`
- `lightweight-charts` v5 类型中不再存在 `addCandlestickSeries`、`addLineSeries`、`addHistogramSeries` 等旧 API
- TanStack Query / Router 调用签名与当前类型不匹配
- 多处 `noUnusedLocals`、`unknown` 类型、路由路径名不一致

## 根因分析

1. TypeScript 升级到 6.x 后，现有 `baseUrl` 配置触发废弃错误。
2. `lightweight-charts` 依赖为 v5.2.0，但图表组件仍使用 v4 风格 API。
3. 前端类型配置较严格，部分测试文件和页面遗留未使用变量。
4. API 适配层的部分类型与真实后端响应/调用入参不同步。

## 修复方案

### 1. 修复 TypeScript 配置

**文件**: `frontend/tsconfig.app.json`

- 迁移 `baseUrl`/`paths` 配置，或临时加入 `ignoreDeprecations: "6.0"` 以恢复构建
- 推荐优先采用兼容 TypeScript 6 的配置方式

### 2. 适配 lightweight-charts v5

**文件**:

- `frontend/src/components/chart/KlineChart.tsx`
- `frontend/src/components/chart/IndicatorPane.tsx`
- `frontend/src/components/backtest/EquityCurve.tsx`
- `frontend/src/components/backtest/DrawdownCurve.tsx`
- `frontend/src/components/watchlist/WatchlistCards.tsx`

将旧 API 替换为 v5 的 `addSeries(...)` 调用，并补齐对应 series 类型。

### 3. 修复 API 客户端类型

**文件**: `frontend/src/api/client.ts`

- `submitBacktest()` 入参类型补充 `strategy_id`，或移除 payload 中未声明字段
- `fetchBacktestResult()` / `useBacktestResult()` 统一 id 类型
- 补齐真实后端返回与 `BacktestResult` 类型映射

### 4. 修复严格类型错误

**文件**: `frontend/src/**/*.ts(x)`

- 清理未使用 import/变量
- 修正 `unknown` 类型排序、日期范围同步、Router path 名称等错误
- 修正 `useStrategies()` 的 queryFn 包装方式

## 验收标准

- [ ] `cd frontend && npm run build` 通过
- [ ] `cd frontend && npm run test` 通过
- [ ] K 线图、回测净值曲线、回撤曲线、指标副图可正常渲染
- [ ] 生产构建产物可通过 `npm run preview` 打开

## 备注

- 审查时间: 2026-05-05
- 该问题会导致 CI 的 frontend build job 失败

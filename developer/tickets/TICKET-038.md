# TICKET-038: 前端 TypeScript 配置与核心类型修复

**优先级:** P1 - 高
**状态:** ✅ 已完成
**依赖:** TICKET-031
**预计工时:** 0.5d

## 需求描述

修复前端构建的基础 TypeScript 阻塞项，让 `tsc` 能继续检查业务代码，并修正 API/client、hooks、router 等核心类型错误。

## 范围边界

**负责文件优先级:**

- `frontend/tsconfig.app.json`
- `frontend/src/api/client.ts`
- `frontend/src/hooks/useStrategies.ts`
- `frontend/src/hooks/useBacktests.ts`
- `frontend/src/hooks/useBacktest.ts`
- `frontend/src/router.ts`
- `frontend/src/lib/docs.ts`
- `frontend/src/types/virtual.d.ts`
- `frontend/src/types/index.ts`

避免修改图表组件；图表 API 迁移由 `TICKET-039` 负责。

## 已知错误

- TypeScript 6 报 `baseUrl` 废弃错误
- `submitBacktest()` payload 使用未声明的 `strategy_id`
- `fetchBacktestResult()` / `useBacktestResult()` id 类型不一致
- `useStrategies()` queryFn 直接传入 `fetchStrategies`，与 TanStack Query v5 调用签名不匹配
- `virtual:docs` 类型声明与导入不一致
- `router.ts` 存在未使用的 `BacktestListPage` 导入

## 任务清单

- [x] 修复 `tsconfig.app.json` 中 TypeScript 6 的 `baseUrl` 废弃阻塞
- [x] 修复 API client 中 backtest 入参/响应映射类型
- [x] 修复 TanStack Query hook 的 queryFn 类型
- [x] 修复 Router 和 virtual docs 类型错误
- [x] 保持 mock 模式与真实 API 模式行为一致

## 验收标准

- [x] `cd frontend && npx tsc -p tsconfig.app.json --noEmit` 不再出现本工单范围内错误
- [x] `cd frontend && npm run test` 通过

## 备注

- 从已取消的 `TICKET-031` 拆分
- 与 `TICKET-039`、`TICKET-040` 并行推进
- 完成时间: 2026-05-05
- 验证结果: `npm run build` 与 `npm run test` 通过

# TICKET-036: 策略详情回测记录未按策略过滤

**优先级:** P2 - 中
**状态:** ✅ 已完成
**依赖:** TICKET-034
**预计工时:** 0.5d

## 症状

前端 `fetchBacktestResults(strategyId)` 在真实 API 模式下忽略 `strategyId`：

```ts
const { data } = await api.get<BacktestHistoryItem[]>('/backtest/history');
return (data ?? []).map(historyItemToResult);
```

同时 `historyItemToResult()` 将所有历史项映射为 `strategy_id: 0`。因此策略详情页会显示全部回测记录，而不是当前策略的记录。

## 根因分析

前端 mock 模式支持 `strategyId` 过滤，但真实 API 模式没有调用 `/api/strategies/{strategy_id}/results`，也没有从后端历史响应中拿到可靠 `strategy_id`。

## 修复方案

### 1. 前端按 strategyId 调用正确接口

**文件**: `frontend/src/api/client.ts`

当传入 `strategyId` 时：

```ts
const { data } = await api.get(`/strategies/${strategyId}/results`);
```

并增加对应 mapper，将后端策略结果映射为 `BacktestResult`。

### 2. 后端补齐策略结果字段

**文件**: `src/zhanfa/api/services/strategy_service.py`

确保 `/api/strategies/{strategy_id}/results` 返回前端列表需要字段：

- `id`
- `strategy_id`
- `stock_codes`
- `params`
- `start_date`
- `end_date`
- `metrics`
- `status`
- `created_at`

如需要详情页跳转，还需确保 `id` 能被 `/api/backtest/{id}` 查询。

### 3. 补充前端测试

**文件**: `frontend/src/api/__tests__/client.test.ts`

覆盖：

- `fetchBacktestResults()` 调用 `/backtest/history`
- `fetchBacktestResults(1)` 调用 `/strategies/1/results`
- 映射后的 `strategy_id` 保持为 1

## 验收标准

- [x] 策略详情页只显示当前策略的回测记录
- [x] 全局回测页仍显示全部历史
- [x] mock 模式与真实 API 模式行为一致
- [x] `cd frontend && npm run test` 通过

## 备注

- 审查时间: 2026-05-05
- 与 TICKET-034 的持久化修复互相依赖

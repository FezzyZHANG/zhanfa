# TICKET-034: 回测结果持久化与策略结果联动

**优先级:** P2 - 中
**状态:** ✅ 已完成
**依赖:** TICKET-020, TICKET-021, TICKET-023
**预计工时:** 1d

## 症状

回测任务当前全部存储在模块级 `_tasks` 字典中：

```python
_tasks: dict[str, dict] = {}
```

服务重启后历史回测全部丢失。与此同时，数据库已有 `backtest_results` 表，但提交回测和完成回测时都没有写入该表。

因此：

- `/api/backtest/history` 只能看到当前进程内存中的任务
- `/api/strategies/{id}/results` 只查 ORM 表，看不到刚刚提交完成的回测
- `backtest_count` 与用户实际回测行为脱节

## 根因分析

TICKET-020/021/023 已补充回测时序字段和响应模型，但 `backtest_service` 仍停留在内存任务管理层，没有和 ORM 持久化打通。

## 修复方案

### 1. 提交任务时创建 DB 记录

**文件**: `src/zhanfa/api/services/backtest_service.py`

在 `submit_backtest()` 中：

- 解析 `strategy_id` 或根据 `strategy` 找到策略记录
- 创建 `BacktestResult(status="pending")`
- 将 DB id 或 task uuid 保存在 `_tasks` 中用于轮询

### 2. 完成任务后更新 DB

在 `run_backtest_async()` 成功后写入：

- `metrics`
- `equity_curve`
- `drawdown_curve`
- `benchmark_curve`
- `yearly_returns`
- `monthly_returns`
- `trades`
- `status="completed"`

失败时写入 `status="failed"` 和错误摘要。

### 3. 历史接口优先读取 DB

**文件**:

- `src/zhanfa/api/routers/backtest.py`
- `src/zhanfa/api/services/backtest_service.py`

`get_history()`、`compare_backtests()`、`get_task()` 应支持：

- 正在运行任务读 `_tasks`
- 已完成历史读 DB

### 4. 策略详情自动联动

**文件**: `src/zhanfa/api/services/strategy_service.py`

确保 `get_strategy_results(strategy_id)` 返回新持久化的回测结果，且字段覆盖前端详情页需要的数据。

## 验收标准

- [ ] 回测完成后 `backtest_results` 表新增/更新记录
- [ ] 服务重启后 `/api/backtest/history` 仍能看到历史结果
- [ ] `/api/strategies/{id}/results` 能看到该策略新跑出的回测
- [ ] `backtest_count` 与 DB 中记录一致
- [ ] 成功和失败任务都可追踪

## 备注

- 审查时间: 2026-05-05
- 与 TICKET-036 前端策略过滤问题相关

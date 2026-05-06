# TICKET-050: 回测结果持久化失败缺少日志与失败语义

**优先级:** P2 - 中
**状态:** ✅ 已完成
**依赖:** TICKET-034
**预计工时:** 0.5d

## 症状

`src/zhanfa/api/services/backtest_service.py` 中回测结果持久化失败时只 rollback，不记录日志：

```py
except Exception:
    session.rollback()
    return None
```

`_update_db_record()` 同样吞掉更新失败。结果是回测任务可能在内存中看似完成，但数据库没有创建或更新记录，服务重启后历史结果丢失，排查时没有异常堆栈。

## 根因分析

`TICKET-034` 已补齐回测结果持久化，但持久化链路仍把数据库异常当作可忽略降级处理。对于后台回测，数据库写入失败是数据一致性问题，至少需要明确日志、任务错误状态或 API 可见的告警。

## 修复方案

### 1. 增加持久化日志

**文件**: `src/zhanfa/api/services/backtest_service.py`

为 `_create_db_record()` 与 `_update_db_record()` 增加 `logger.exception(...)`，包含：

- `task_id`
- `db_id`
- `strategy_id`
- `stock code`
- 更新字段名

### 2. 明确失败语义

评估两种方案：

- 创建记录失败：`submit_backtest()` 直接抛出异常，让 API 返回 500
- 更新记录失败：内存任务继续保留，但 `task["error"]` 或日志暴露持久化失败

### 3. 补充测试

用 mock session 抛异常，验证：

- rollback 被调用
- 日志包含异常上下文
- API/任务状态符合约定

## 实施结果

### `_create_db_record`
- 新增 `logger.exception("Failed to create backtest db record: task_id=... strategy_id=... code=...")` 
- 创建失败时 `submit_backtest` 额外记录 warning，指明任务将以无持久化模式运行

### `_update_db_record`
- 新增 `logger.exception("Failed to update backtest db record: db_id=... fields=...")`
- 新增 `logger.warning` 处理 `db_id` 不存在的边界情况

### `run_backtest_async`
- 执行异常新增 `logger.exception("Backtest execution failed: task_id=... strategy=... code=...")` 含完整堆栈

## 验收标准

- [x] `_create_db_record()` 和 `_update_db_record()` 不再静默吞掉数据库异常
- [x] 回测提交或完成阶段的持久化失败有明确日志
- [x] 服务重启导致历史丢失的问题可通过日志定位到数据库写入失败
- [x] `uv run pytest tests/test_api/test_endpoints.py tests/test_services/test_backtest_service.py -v` → 37 passed

## 备注

- 本工单不重新设计持久化模型，只补齐失败可观测性与语义
- 审查时间: 2026-05-06

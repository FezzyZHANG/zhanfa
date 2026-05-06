# TICKET-013: 完善测试覆盖

| 属性     | 值                              |
| -------- | ------------------------------- |
| 优先级   | P1 - 高                         |
| 依赖     | 003, 010, 012                   |
| 创建日期 | 2026-05-05                      |

## 问题描述

当前测试覆盖严重不足：

**已有测试的问题：**
- `tests/test_api/test_endpoints.py:127-130` — `test_get_stock_not_found` 接受 200 和 404 两种状态码，形同虚设
- `tests/test_strategies/` — 只有 `test_sma_cross.py`，缺少 Turtle 策略测试

**完全缺失的测试：**
- 策略模块：无 Turtle、无新策略（momentum/fundamental/composite）测试
- 服务模块：无 `import_data.py`、`watchlist_service.py`、`strategy_service.py`、`backtest_service.py` 测试
- 自动化模块：无 `scheduler.py`、`workflows.py` 测试
- 策略注册：无 `register_strategies.py` 测试
- 前端代码：完全无测试
- `src/backtest/metrics.py:28` — `returns` 为空时返回 `{}`，调用方可能出现 KeyError

## 任务清单

- [ ] 修复 `test_get_stock_not_found` 为严格 `assert r.status_code == 404`
- [ ] 为 `Turtle` 策略编写测试 (`tests/test_strategies/test_turtle.py`)
- [ ] 为 `import_data.py` 编写测试
- [ ] 为 `watchlist_service.py` 编写测试
- [ ] 为 `strategy_service.py` 编写测试
- [ ] 为 `backtest_service.py` 编写测试
- [ ] 为 `scheduler.py` 编写测试
- [ ] 为 `workflows.py` 编写测试
- [ ] 为 `register_strategies.py` 编写测试
- [ ] 修复 `backtest/metrics.py` 空 returns 的异常处理

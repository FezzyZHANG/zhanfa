# TICKET-014: 增强回测引擎与自动化流程

| 属性     | 值                              |
| -------- | ------------------------------- |
| 优先级   | P2 - 中                         |
| 依赖     | 003                            |
| 创建日期 | 2026-05-05                      |

## 问题描述

### 回测引擎局限 (`src/zhanfa/backtest/engine.py`)
- 仅支持单只股票回测，不支持多资产组合回测
- 不支持多时间框架分析
- `compare_strategies()` 实现过于简单
- 没有仓位管理逻辑
- 没有止损/止盈支持（超出 vectorbt 内置功能的部分）

### 自动化流程不完整 (`src/zhanfa/automation/`)
- `workflows.py:update_daily_data()` — 只更新已有缓存中的股票，无新股票发现逻辑，错误处理仅有日志
- `workflows.py:weekly_index_rebalance()` — 仅获取指数成分并打印数量，未执行实际的调仓操作
- `scheduler.py` — 无持久化存储、无错误通知机制、无日志配置

### 财务数据字段缺失 (`src/zhanfa/data/fetcher.py`)
- `_clean_financial()` 方法的列映射不完整，缺少 PE、PB、毛利率、股息率等字段
- 这些字段在 `StockFinancial` ORM 模型和前端类型中已定义，但未被实际获取

## 任务清单

- [x] 回测引擎：支持多资产组合回测（组合权重分配）
- [x] 回测引擎：添加止损/止盈策略参数
- [x] `workflows.py`：实现完整的日数据更新流程（含新股票发现）
- [x] `workflows.py`：实现 `weekly_index_rebalance` 的实际调仓逻辑
- [x] `scheduler.py`：添加持久化存储和错误通知
- [x] `fetcher.py`：完善 `_clean_financial()` 的列映射，提取 PE、PB、毛利率、股息率

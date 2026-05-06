# TICKET-015: JQ Adapter 完善与杂项修复

| 属性     | 值                              |
| -------- | ------------------------------- |
| 优先级   | P3 - 低                         |
| 依赖     | -                              |
| 创建日期 | 2026-05-05                      |

## 问题描述

### JQ Adapter 生成骨架代码 (`src/zhanfa/jq/adapter.py:34`)
`JoinQuant` 适配器生成的回测代码只有 TODO 骨架：
```python
# if 买入条件:
#     order_value(g, security, context.portfolio.available_cash / len(g.stocks))
# elif 卖出条件:
#     order_target(g, security, 0)
```
用户需手动填写买卖逻辑。

### `fit()` 空方法 (`src/zhanfa/strategies/base.py:35-37`)
`BaseStrategy.fit()` 方法体为 `pass`，为未来 ML 策略预留的接口至今未有调用方。

### 策略自动注册发现机制
当前策略注册依赖 `register_strategies.py` 的手动导入，没有自动发现机制来扫描策略包下的所有策略类。

## 任务清单

- [x] JQ Adapter：从 `BaseStrategy.generate_signals()` 的返回结果中自动生成 trading logic，而不是只输出 TODO — 生成结构化的参数声明、条件提示和完整买卖执行代码
- [x] 为 `fit()` 方法添加调用方或在 ML 策略实现前标记为预留接口 — 已更新 docstring，标记为 `[预留接口]` 供未来 ML 策略使用
- [x] 实现策略自动发现（扫描 `strategies/` 下所有 `BaseStrategy` 子类） — 已通过 `db/register_strategies.py` 实现

# TICKET-010: 实现缺失的策略类型

| 属性     | 值                              |
| -------- | ------------------------------- |
| 优先级   | P2 - 中                         |
| 依赖     | -                               |
| 创建日期 | 2026-05-05                      |

## 问题描述

现有策略目录有三个空包，仅有 `__init__.py` 中的 docstring，没有实际策略实现：

| 包 | 路径 | 应有内容 |
|---|------|---------|
| `momentum` | `src/zhanfa/strategies/momentum/` | RSI 超买超卖策略、MACD 策略 |
| `fundamental` | `src/zhanfa/strategies/fundamental/` | 低估值策略 (Low PE)、PEG 策略 |
| `composite` | `src/zhanfa/strategies/composite/` | 趋势+基本面组合、动量+低波组合 |

前端 mock 数据 (`frontend/src/api/mock.ts`) 中引用了这些策略：
- id:3 "RSI 超买超卖策略" — code_ref 错误指向 `SMACross`，应为动量策略
- id:4 低估值策略 — backtest_count: 0
- id:5 PEG 策略 — backtest_count: 0
- id:6-8 组合策略 — backtest_count: 0

## 任务清单

- [x] 在 `momentum/` 下实现 `rsi_strategy.py` — RSI 超买超卖策略（继承 `BaseStrategy`）
- [x] 在 `momentum/` 下实现 `macd_strategy.py` — MACD 金叉死叉策略
- [x] 在 `fundamental/` 下实现 `low_pe_strategy.py` — 低市盈率选股策略
- [x] 在 `fundamental/` 下实现 `peg_strategy.py` — PEG 选股策略
- [x] 在 `composite/` 下实现 `trend_fundamental.py` — 趋势+基本面组合策略
- [x] 在 `composite/` 下实现 `momentum_lowvol.py` — 动量+低波动组合策略
- [x] 策略自动注册 — `db/register_strategies.py` 通过 `pkgutil.walk_packages` 自动发现所有 `BaseStrategy` 子类
- [x] 修复前端 mock.ts 中策略 3-8 的 code_ref 指向正确的策略类
- [x] 为每个新策略编写基础测试

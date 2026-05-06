# TICKET-033: 修复回测止损/止盈参数语义

**优先级:** P1 - 高
**状态:** ✅ 已完成
**依赖:** TICKET-014
**预计工时:** 0.5d

## 症状

回测引擎中用户传入 `sl_stop=0.1`、`tp_stop=0.3` 时，代码会转换为：

```python
vb_sl = 1 - sl_stop
vb_tp = 1 + tp_stop
```

这会把 10% 止损变成 90% 阈值，把 30% 止盈变成 130% 阈值。

## 根因分析

`vectorbt.Portfolio.from_signals()` 的 `sl_stop` / `tp_stop` 参数语义是相对入场价的百分比距离。用户输入 `0.1` 本身就代表 10%，无需转换成 `0.9`。

同样问题存在于单标的和组合回测路径。

## 修复方案

**文件**: `src/zhanfa/backtest/engine.py`

### 1. 去除错误转换

将：

```python
vb_sl = 1 - sl_stop if sl_stop is not None else None
vb_tp = 1 + tp_stop if tp_stop is not None else None
```

改为：

```python
vb_sl = sl_stop
vb_tp = tp_stop
```

### 2. 补充行为测试

**文件**: `tests/test_backtest/test_engine.py`

- 构造明显跌破 10% 的价格序列，验证 `sl_stop=0.1` 会触发提前退出
- 构造明显上涨超过 30% 的价格序列，验证 `tp_stop=0.3` 会触发止盈
- 覆盖 `run_portfolio_backtest()` 的同类路径

### 3. 更新文档说明

**文件**:

- `docs/backtest.md`
- `developer/architecture.md` 或相关回测开发文档

明确参数语义：`0.1` 表示 10%，不是价格比例 0.9。

## 验收标准

- [x] `sl_stop=0.1` 按 10% 止损生效
- [x] `tp_stop=0.3` 按 30% 止盈生效
- [x] 单标的和组合回测都使用一致语义
- [x] `uv run pytest tests/test_backtest -q` 通过

## 备注

- 审查时间: 2026-05-05
- 该问题会直接影响回测结果可信度，优先级较高

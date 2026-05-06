# TICKET-020: 后端回测服务补充时序数据提取

**优先级:** P1 - 高
**状态:** 📋 待开始
**依赖:** -
**预计工时:** 0.5d

## 需求描述

当前 `_execute_backtest` 在 [backtest_service.py:86-104](../../src/zhanfa/api/services/backtest_service.py#L86-L104) 中调用了 `compute_metrics(equity)` 后只返回 9 个标量指标，丢弃了 `pf` (vectorbt Portfolio) 对象中已有的净值曲线、回撤曲线、交易记录等数据，导致前端回测详情页的所有图表（净值曲线、回撤曲线、年度收益柱状图、月度热力图、交易记录表格）全部为空。

## 根因分析

```
_execute_backtest
  → pf = run_backtest_from_strategy(df, strategy, ...)
  → equity = pf.value()                  # 取权益曲线
  → metrics = compute_metrics(equity)    # 只算 9 个标量
  → return metrics                       # pf 被丢弃，时序/交易数据全部丢失
```

`compute_metrics` (metrics.py:48-50) 内部也计算了 `drawdown` 系列但未返回调用方。

## 功能清单

### 1. 从 Portfolio 提取净值曲线
- `pf.value()` 已是权益曲线 (pd.Series)，转换为 `{date, value}` 列表
- 同时提取基准净值曲线（如有）

### 2. 从权益曲线派生回撤曲线
- 由 `equity / cummax - 1` 计算，或直接从 `pf.drawdown()` 获取
- 转换为 `{date, value}` 列表

### 3. 从权益曲线计算年度/月度收益
- 年度收益：按年重采样收益率 → `[{year, value}]`
- 月度收益：按月重采样收益率 → `[{year, month, value}]`

### 4. 从 Portfolio 提取交易记录
- `pf.trades.records` 包含每笔交易的日期、方向、价格、数量、盈亏
- 转换为 `[{date, action, price, quantity, pnl}]`

### 5. 将数据存入 task dict
- 在 `_execute_backtest` 返回值中增加 `equity_curve`, `drawdown_curve`, `benchmark_curve`, `yearly_returns`, `monthly_returns`, `trades`
- 同步更新 `run_backtest_async` (line 47) 中 `task["metrics"]` 的存法——考虑将 metrics + curves 分开存，或将整个结果存为一个大 dict

## 技术方案

```python
def _execute_backtest(req: dict) -> dict:
    # ... existing fetch & run ...
    pf = run_backtest_from_strategy(df, strategy, ...)
    equity = pf.value()
    metrics = compute_metrics(equity)
    
    # 新增：提取时序数据
    equity_curve = [{"date": str(d.date()), "value": round(v, 4)} 
                    for d, v in equity.items()]
    
    drawdown = pf.drawdown()  # 或手算
    drawdown_curve = [{"date": str(d.date()), "value": round(v, 4)} 
                      for d, v in drawdown.items()]
    
    # 年度/月度收益
    yearly = equity.resample("YE").apply(lambda x: x.iloc[-1] / x.iloc[0] - 1)
    monthly = equity.resample("ME").apply(lambda x: x.iloc[-1] / x.iloc[0] - 1)
    
    # 交易记录
    trades = pf.trades.records  # DataFrame → list of dicts
    
    return {
        "metrics": {k: float(v) ... for k, v in metrics.items()},
        "equity_curve": equity_curve,
        "drawdown_curve": drawdown_curve,
        "benchmark_curve": benchmark_curve,  # if available
        "yearly_returns": yearly_returns,
        "monthly_returns": monthly_returns,
        "trades": trades_list,
    }
```

## 验收标准

- [ ] `_execute_backtest` 返回 dict 包含所有时序数据字段
- [ ] 权益曲线数据点数量 ≈ 回测天数
- [ ] 交易记录包含每笔买卖的方向、价格、数量、盈亏
- [ ] 年度/月度收益与 metrics 中的 total_return 一致（各期几何累乘 = 总收益）
- [ ] `run_backtest_async` 正确将新字段存入 task dict
- [ ] 在 `uv run python -c` 下单测验证数据格式正确

## 备注

- vectorbt Portfolio 对象 `pf.trades.records` 返回 DataFrame，需处理为空的情况（无交易时）
- 月度收益热力图需要 `{year, month, value}` 格式，注意 `resample("ME")` 的索引提取
- 数据量：回测 5 年约 1200+ 个数据点，JSON 传输无压力

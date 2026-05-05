# 回测与验证

## 本地回测 (vectorbt 0.28)

### 单策略回测

```python
from zhanfa.data.fetcher import Fetcher
from zhanfa.data.pipeline import Pipeline
from zhanfa.strategies.trend.sma_cross import SMACross
from zhanfa.backtest.engine import run_backtest_from_strategy
from zhanfa.backtest.report import generate_report

# 数据准备
df = Fetcher().index_daily("000300")
df = Pipeline.clean(df)

# 回测（可带止损/止盈）
pf = run_backtest_from_strategy(
    df, SMACross(fast=20, slow=60),
    sl_stop=0.1,   # 亏 10% 止损
    tp_stop=0.3,   # 盈 30% 止盈
)

# 结果
pf.value().plot()       # 权益曲线
pf.drawdown().plot()    # 回撤曲线
pf.trades.records       # 交易记录
print(generate_report(pf))  # Markdown 报告
```

`sl_stop` / `tp_stop` 使用 vectorbt 的百分比距离语义：`0.1` 表示相对入场价 10%，`0.3` 表示 30%，不会转换为价格比例 `0.9` / `1.3`。

### 多资产组合回测

```python
from zhanfa.backtest.engine import run_portfolio_backtest

# prices: 每列一只股票
prices = pd.DataFrame({
    "000001": close_series_1,
    "600519": close_series_2,
})

# signals: 同样 shape 的布尔 DataFrame（True=持有）
signals = pd.DataFrame({
    "000001": strategy1.generate_signals(data1),
    "600519": strategy2.generate_signals(data2),
})

# 等权组合
pf = run_portfolio_backtest(prices, signals)

# 自定义权重
pf = run_portfolio_backtest(
    prices, signals,
    weights={"000001": 0.6, "600519": 0.4},
    sl_stop=0.1,
    tp_stop=0.3,
)
```

### 多策略对比

```python
from zhanfa.backtest.engine import compare_strategies
from zhanfa.strategies.trend.turtle import Turtle

results = compare_strategies(
    df["close"],
    [
        SMACross(fast=5, slow=20),
        SMACross(fast=20, slow=60),
        Turtle(),
    ]
)
print(results)  # DataFrame，每行一个策略的统计摘要
```

### vectorbt 常用 API

| 调用 | 返回 | 说明 |
|---|---|---|
| `pf.value()` | Series | 权益曲线（替代旧版 `equity()`） |
| `pf.drawdown()` | Series | 回撤序列 |
| `pf.stats()` | Series | 完整绩效统计 |
| `pf.trades.records` | DataFrame | 每笔交易明细 |
| `pf.trades.win_rate()` | float | 胜率 |

### 回测参数

在 `src/zhanfa/config.py` 中全局可配：

| 参数 | 默认值 | 说明 |
|---|---|---|
| `initial_capital` | 100,000 | 初始资金 |
| `commission` | 0.0005 | 手续费率（单向） |
| `slippage` | 0.001 | 滑点率 |
| `risk_free_rate` | 0.017 | 无风险利率（用于夏普计算） |

回测函数的 `sl_stop` / `tp_stop` 可在调用时传入，数值表示相对入场价的百分比距离。例如 `sl_stop=0.1` 是 10% 止损，`tp_stop=0.3` 是 30% 止盈。

调用时可按需覆盖：
```python
pf = run_backtest_from_strategy(df, strategy, initial_capital=500000, commission=0.0003)
```

## 绩效指标

`compute_metrics(value_series)` 返回 dict：

| 指标 | 键 | 说明 |
|---|---|---|
| 总收益率 | `total_return` | 期末/期初 - 1 |
| 年化收益率 | `ann_return` | 几何年化 |
| 年化波动率 | `ann_volatility` | 日收益率 std × √252 |
| 夏普比率 | `sharpe` | (年化收益 - 无风险利率) / 年化波动 |
| 索提诺比率 | `sortino` | 仅用下行波动率 |
| 最大回撤 | `max_drawdown` | 峰谷最大跌幅 |
| 卡玛比率 | `calmar` | 年化收益 / 最大回撤 |
| 胜率 | `win_rate` | 日收益 > 0 的比例 |

传入 benchmark 可额外获得 `excess_return` 和 `ann_excess`。

## CLI 入口

```bash
# 回测沪深300指数
uv run python scripts/run_backtest.py

# 回测指定指数
uv run python scripts/run_backtest.py 000905

# 导出 JoinQuant 策略
uv run python scripts/export_jq.py sma_cross
uv run python scripts/export_jq.py turtle
```

## JoinQuant 云端验证

```
本地开发 → CLI 回测 → notebook 调参 → 导出 JQ 代码 → 聚宽仿真 → 实盘
```

`jq/adapter.py` 将策略参数和方法签名翻译为 JQ 代码骨架：

```python
from zhanfa.jq.adapter import to_jq_template
from zhanfa.strategies.trend.sma_cross import SMACross

code = to_jq_template(SMACross(fast=5, slow=20))
# 生成包含 initialize() + handle_data() 的完整骨架
```

生成的代码包含：
- 策略参数自动内联为局部变量
- 结构化的 `order_value()` / `order_target()` 交易执行逻辑
- 根据参数名推断的买卖条件提示（如 MACD → DIF 上穿 DEA、MA → 价格上穿均线）

用户仅需根据提示填入具体的入场/出场判断条件，即可在 JoinQuant 研究环境运行。

## API 回测端点

```bash
# 提交回测任务（异步执行）
curl -X POST http://127.0.0.1:8000/api/backtest/run \
  -H "Content-Type: application/json" \
  -d '{"code":"000001","strategy":"sma_cross","start_date":"20240101","end_date":"20250101"}'

# 查询任务状态
curl http://127.0.0.1:8000/api/backtest/{task_id}

# 历史回测记录
curl http://127.0.0.1:8000/api/backtest/history
```

回测在后台线程异步执行（`BackgroundTasks` + `run_in_executor`），不阻塞 HTTP 请求。提交后立即返回 `task_id`，前端轮询 `GET /api/backtest/{task_id}` 获取结果。

### 回测持久化

回测结果持久化到 `backtest_results` 表，服务重启后历史记录不丢失：

- **提交时**：创建 `status="pending"` 的 DB 记录，关联 `strategy_id` 和 `task_id`
- **完成后**：写入 `metrics`、`equity_curve`、`drawdown_curve`、`yearly_returns`、`monthly_returns`、`trades`，`status="completed"`
- **失败时**：写入 `status="failed"` 和错误摘要
- **查询时**：`/api/backtest/history` 合并内存任务（pending/running）和 DB 记录（completed/failed），内存任务优先
- `/api/strategies/{id}/results` 自动联动，显示该策略的所有持久化回测结果，包含完整曲线和交易数据

完成后的响应包含标量指标和时序数据：

```json
{
  "task_id": "abc12345",
  "status": "completed",
  "metrics": { "total_return": 0.15, "sharpe": 1.2, "max_drawdown": -0.08, ... },
  "equity_curve": [{"date": "2024-01-02", "value": 100000.0}, ...],
  "drawdown_curve": [{"date": "2024-01-02", "value": 0.0}, ...],
  "yearly_returns": [{"year": 2024, "value": 0.15}],
  "monthly_returns": [{"year": 2024, "month": 1, "value": 0.02}, ...],
  "trades": [{"date": "2024-03-15", "action": "buy", "price": 12.5, "quantity": 800, "pnl": null}, ...]
}
```

## 参数优化

vectorbt 原生支持参数网格搜索，可直接在 notebook 中使用：

```python
import vectorbt as vbt
import numpy as np

fast_range = np.arange(5, 51, 5)
slow_range = np.arange(20, 121, 10)

pf = vbt.Portfolio.from_signals(
    price,
    entries=...,  # 按 fast/slow 组合生成
    exits=...,
    freq="d",
)
# pf.total_return 是一个 fast × slow 的热力图矩阵
```

这部分后续会封装为 `backtest/engine.py` 中的 `optimize()` 函数。

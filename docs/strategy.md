# 策略编写指南

## 策略基类

所有择时策略继承 `BaseStrategy`，实现唯一方法 `generate_signals`：

```python
from zhanfa.strategies.base import BaseStrategy
import pandas as pd

class MyStrategy(BaseStrategy):
    name = "my_strategy"

    def __init__(self, param1=10):
        self.param1 = param1

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """
        data: OHLCV DataFrame, index=日期
        return: pd.Series[bool], True=持有, False=空仓
        """
        close = data["close"]
        return close > close.rolling(self.param1).mean()
```

### 接口约定

- **输入**: `pd.DataFrame`，index 为 `DatetimeIndex`，列含 `open/high/low/close/volume`（已由 Pipeline 清洗）
- **输出**: `pd.Series[bool]`，index 对齐 `data.index`
- **仓位权重** (可选): 覆写 `position_weights(data) → pd.DataFrame` 做多标的分配
- **训练** (可选): 覆写 `fit(data)` 做历史参数拟合

### 回测集成

策略不依赖 vectorbt，但输出格式预期可被直接消费：

```python
from zhanfa.backtest.engine import run_backtest_from_strategy

pf = run_backtest_from_strategy(df, MyStrategy(param1=20))
pf.value().plot()   # 权益曲线
pf.stats()          # 绩效统计
```

## 指标库

`zhanfa.strategies.indicators` 提供纯函数指标，输入输出均为 `pd.Series`：

```python
from zhanfa.strategies.indicators import (
    sma, ema, rsi, macd, bollinger, donchian, atr, highest, lowest
)

ma_fast = sma(df["close"], 20)
ma_slow = ema(df["close"], 60)
r = rsi(df["close"], 14)
macd_df = macd(df["close"])        # DataFrame[dif, dea, bar]
bb = bollinger(df["close"])        # DataFrame[upper, mid, lower]
dc = donchian(df["high"], df["low"], 20)  # 唐奇安通道
```

## 策略分类

| 目录 | 流派 | 现有策略 |
|---|---|---|
| `trend/` | 趋势跟踪 | `SMACross`（双均线）、`Turtle`（海龟） |
| `momentum/` | 动量/反转 | `RSIStrategy`（RSI 超买超卖）、`MACDStrategy`（MACD 金叉死叉） |
| `fundamental/` | 基本面选股 | `LowPEStrategy`（低市盈率）、`PEGStrategy`（PEG 成长） |
| `composite/` | 多因子综合 | `TrendFundamental`（趋势+基本面共振）、`MomentumLowVol`（动量+低波多因子） |

## 添加新策略

1. 在对应流派目录创建 `.py` 文件
2. 继承 `BaseStrategy`，设置 `name`，实现 `generate_signals`
3. 编写详细的 docstring（用于前端策略详情页的 Markdown 渲染），包含 Parameters 段描述每个参数
4. 可选：在目录 `__init__.py` 中导出
5. 重启服务，策略自动注册到数据库（通过 `db/register_strategies.py` 自动扫描 `BaseStrategy` 子类）

示例 — 双均线交叉：
```python
# strategies/trend/sma_cross.py
from zhanfa.strategies.base import BaseStrategy
from zhanfa.strategies.indicators import sma

class SMACross(BaseStrategy):
    """双均线交叉策略：短线上穿长线买入，下穿卖出。

    Parameters:
        fast: 快线周期（默认 20）
        slow: 慢线周期（默认 60）
    """

    name = "sma_cross"

    def __init__(self, fast: int = 20, slow: int = 60):
        self.fast = fast
        self.slow = slow

    def generate_signals(self, data):
        fast_ma = sma(data["close"], self.fast)
        slow_ma = sma(data["close"], self.slow)
        signals = (fast_ma > slow_ma).ffill().fillna(False)
        return signals
```

## 基本面策略（方向）

基本面策略与择时策略的输出形式不同——输出的是**股票池**而非日级信号。后续会引入 `BaseScreener` 接口：

```python
class BaseScreener(ABC):
    name: str

    @abstractmethod
    def screen(self, financials, prices, date) -> pd.Series:
        """返回 Series[float], index=code, value=score/weight"""
```

择时策略在筛选后的股票池上运行，实现"基本面选股 + 技术面择时"的组合。

## API 策略端点

策略通过 API 可被前端发现和调用：

```bash
# 列出所有策略（支持 ?category=trend 和 ?search=关键词 过滤）
curl http://127.0.0.1:8000/api/strategies

# 策略详情 + 参数 schema（供前端动态生成配置表单）
curl http://127.0.0.1:8000/api/strategies/1

# 策略的回测结果
curl http://127.0.0.1:8000/api/strategies/1/results
```

## 自动注册

后端启动时自动扫描 `zhanfa.strategies` 包下所有 `BaseStrategy` 子类，无需手动注册：

```python
# db/register_strategies.py — 启动时自动执行
register_strategies("zhanfa.strategies")
```

注册逻辑：
1. 遍历 `zhanfa.strategies.trend`、`momentum`、`fundamental`、`composite` 子包
2. 找到所有 `BaseStrategy` 子类
3. 从模块路径推断 category（如 `zhanfa.strategies.trend.SMACross` → `trend`）
4. 从 `__init__` 签名提取参数（名称、类型、默认值）
5. 从 docstring 提取描述和参数说明
6. Upsert 到 `strategies` 表

新增策略只需在对应目录创建 `.py` 文件继承 `BaseStrategy`，重启服务即自动可见。

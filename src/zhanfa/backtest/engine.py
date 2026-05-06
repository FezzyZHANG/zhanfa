"""回测引擎 - vectorbt 封装"""

import pandas as pd
import vectorbt as vbt

from zhanfa.strategies.base import BaseStrategy
from zhanfa.config import config


def run_backtest(
    price: pd.Series,
    signals: pd.Series,
    freq: str = "d",
    initial_capital: float | None = None,
    commission: float | None = None,
    slippage: float | None = None,
    sl_stop: float | None = None,
    tp_stop: float | None = None,
) -> vbt.Portfolio:
    """单标的回测。

    Args:
        price: 收盘价序列
        signals: 布尔信号序列（True=持有）
        freq: 频率 'd' 日线
        initial_capital: 初始资金
        commission: 手续费率
        slippage: 滑点率
        sl_stop: 止损阈值（如 0.1 表示亏10%止损）
        tp_stop: 止盈阈值（如 0.3 表示盈30%止盈）

    Returns:
        vectorbt Portfolio 对象
    """
    initial_capital = initial_capital or config.initial_capital
    commission = commission if commission is not None else config.commission
    slippage = slippage if slippage is not None else config.slippage

    entries = signals & ~signals.shift(1).fillna(False)
    exits = ~signals & signals.shift(1).fillna(False)

    pf = vbt.Portfolio.from_signals(
        price,
        entries=entries,
        exits=exits,
        freq=freq,
        init_cash=initial_capital,
        fees=commission,
        slippage=slippage,
        sl_stop=sl_stop,
        tp_stop=tp_stop,
    )
    return pf


def run_backtest_from_strategy(
    price: pd.Series | pd.DataFrame,
    strategy: BaseStrategy,
    freq: str = "d",
    initial_capital: float | None = None,
    commission: float | None = None,
    slippage: float | None = None,
    sl_stop: float | None = None,
    tp_stop: float | None = None,
) -> vbt.Portfolio:
    """从策略对象直接回测。

    Args:
        price: 收盘价序列或完整行情 DataFrame
        strategy: 策略实例
    """
    if isinstance(price, pd.DataFrame) and "close" in price.columns:
        signals = strategy.generate_signals(price)
        price_series = price["close"]
    else:
        signals = strategy.generate_signals(
            price.to_frame("close").pipe(  # type: ignore[operator]
                lambda d: d.assign(  # type: ignore[call-overload]
                    open=price,  # type: ignore[arg-type]
                    high=price,  # type: ignore[arg-type]
                    low=price,  # type: ignore[arg-type]
                    volume=1,  # type: ignore[arg-type]
                )
            )
        )
        price_series = price if isinstance(price, pd.Series) else price["close"]

    return run_backtest(
        price_series,
        signals,
        freq,
        initial_capital,
        commission,
        slippage,
        sl_stop=sl_stop,
        tp_stop=tp_stop,
    )


def run_portfolio_backtest(
    prices: pd.DataFrame,
    signals: pd.DataFrame,
    weights: dict[str, float] | None = None,
    freq: str = "d",
    initial_capital: float | None = None,
    commission: float | None = None,
    slippage: float | None = None,
    sl_stop: float | None = None,
    tp_stop: float | None = None,
) -> vbt.Portfolio:
    """多资产组合回测。

    Args:
        prices: DataFrame，每列一只股票的收盘价，列名为股票代码
        signals: 布尔 DataFrame（True=持有），与 prices 同 shape
        weights: 权重分配 {code: weight}，None 则等权分配
        freq: 频率
        initial_capital: 初始资金
        commission: 手续费率
        slippage: 滑点率
        sl_stop: 止损阈值
        tp_stop: 止盈阈值

    Returns:
        vectorbt Portfolio 对象
    """
    initial_capital = initial_capital or config.initial_capital
    commission = commission if commission is not None else config.commission
    slippage = slippage if slippage is not None else config.slippage

    common = prices.columns.intersection(signals.columns)
    if len(common) == 0:
        raise ValueError("prices and signals share no common columns")

    if weights is None:
        weights = {c: 1.0 / len(common) for c in common}

    entries = signals & ~signals.shift(1).fillna(False)
    exits = ~signals & signals.shift(1).fillna(False)

    size = pd.DataFrame(0.0, index=entries.index, columns=common)
    for col in common:
        size[col] = weights.get(col, 0.0)

    pf = vbt.Portfolio.from_signals(
        prices[common],
        entries=entries[common],
        exits=exits[common],
        size=size,
        size_type="percent",
        freq=freq,
        init_cash=initial_capital,
        fees=commission,
        slippage=slippage,
        sl_stop=sl_stop,
        tp_stop=tp_stop,
    )
    return pf


def compare_strategies(
    price: pd.Series | pd.DataFrame,
    strategies: list[BaseStrategy],
    freq: str = "d",
) -> pd.DataFrame:
    """多策略对比回测。

    Returns:
        DataFrame，每行一个策略的绩效指标摘要。
    """
    results = []
    for s in strategies:
        pf = run_backtest_from_strategy(price, s, freq)
        stats = pf.stats()
        stats["strategy"] = s.name
        results.append(stats)

    return pd.DataFrame(results).set_index("strategy")

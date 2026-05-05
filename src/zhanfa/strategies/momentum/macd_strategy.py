"""MACD 金叉死叉策略"""

import pandas as pd

from zhanfa.strategies.base import BaseStrategy
from zhanfa.strategies.indicators import macd


class MACDStrategy(BaseStrategy):
    """MACD 金叉死叉策略：DIF 上穿 DEA 做多，下穿平多。

    Parameters:
        fast: 快线 EMA 周期（默认 12）
        slow: 慢线 EMA 周期（默认 26）
        signal: 信号线 EMA 周期（默认 9）
    """

    name = "MACD 金叉死叉策略"

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        self.fast = fast
        self.slow = slow
        self.signal = signal

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        macd_df = macd(data["close"], self.fast, self.slow, self.signal)
        dif = macd_df["dif"]
        dea = macd_df["dea"]

        entries = dif > dea
        exits = dif < dea

        signals = pd.Series(False, index=data.index)
        signals[entries] = True
        signals[exits] = False
        signals = signals.ffill().fillna(False)

        return signals

"""RSI 超买超卖策略"""

import pandas as pd

from zhanfa.strategies.base import BaseStrategy
from zhanfa.strategies.indicators import rsi


class RSIStrategy(BaseStrategy):
    """RSI 超买超卖策略：RSI 低于超卖阈值买入，高于超买阈值卖出。

    Parameters:
        rsi_period: RSI 计算周期（默认 14）
        oversold: 超卖阈值（默认 30）
        overbought: 超买阈值（默认 70）
    """

    name = "RSI 超买超卖策略"

    def __init__(self, rsi_period: int = 14, oversold: int = 30, overbought: int = 70):
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        rsi_series = rsi(data["close"], self.rsi_period)

        entries = rsi_series < self.oversold
        exits = rsi_series > self.overbought

        signals = pd.Series(False, index=data.index)
        signals[entries] = True
        signals[exits] = False
        signals = signals.ffill().fillna(False)

        return signals

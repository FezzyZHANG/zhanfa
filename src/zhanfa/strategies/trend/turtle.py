"""海龟交易策略"""

import pandas as pd

from zhanfa.strategies.base import BaseStrategy
from zhanfa.strategies.indicators import donchian, atr


class Turtle(BaseStrategy):
    """经典海龟交易法则。

    Parameters:
        entry_period: 入场通道周期（默认 20）
        exit_period: 离场通道周期（默认 10）
        atr_period: ATR 周期（默认 20）
        atr_mult: 止损 ATR 倍数（默认 2）
    """

    name = "海龟交易法则"

    def __init__(self, entry_period: int = 20, exit_period: int = 10, atr_period: int = 20, atr_mult: float = 2.0):
        self.entry_period = entry_period
        self.exit_period = exit_period
        self.atr_period = atr_period
        self.atr_mult = atr_mult

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        entry_ch = donchian(data["high"], data["low"], self.entry_period)
        exit_ch = donchian(data["high"], data["low"], self.exit_period)

        entries = data["close"] > entry_ch["upper"].shift(1)
        exits = data["close"] < exit_ch["lower"].shift(1)

        signals = pd.Series(False, index=data.index)
        signals[entries] = True
        signals[exits] = False
        signals = signals.ffill().fillna(False)

        return signals

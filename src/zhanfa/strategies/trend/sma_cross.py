"""双均线交叉策略 - 趋势跟踪入门示例"""

import pandas as pd

from zhanfa.strategies.base import BaseStrategy
from zhanfa.strategies.indicators import sma


class SMACross(BaseStrategy):
    """双均线交叉策略：短线上穿长线买入，下穿卖出。

    Parameters:
        fast: 快线周期（默认 20）
        slow: 慢线周期（默认 60）
    """

    name = "双均线交叉策略"

    def __init__(self, fast: int = 20, slow: int = 60):
        self.fast = fast
        self.slow = slow

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"]
        fast_ma = sma(close, self.fast)
        slow_ma = sma(close, self.slow)

        entries = fast_ma > slow_ma
        exits = fast_ma < slow_ma

        signals = pd.Series(False, index=data.index)
        signals[entries] = True
        signals[exits] = False
        signals = signals.ffill().fillna(False)

        return signals

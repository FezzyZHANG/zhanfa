"""彼得·林奇 PEG 策略"""

import pandas as pd

from zhanfa.strategies.base import BaseStrategy


class PEGStrategy(BaseStrategy):
    """PEG 选股策略：筛选 PEG < max_peg 且盈利增长 > min_growth 的成长标的。

    Parameters:
        max_peg: 最大 PEG 值（默认 1）
        min_growth: 最小盈利增长率（默认 0.1）
        max_pe: 最大市盈率上限（默认 30）
    """

    name = "彼得·林奇 PEG 策略"

    def __init__(self, max_peg: float = 1, min_growth: float = 0.1, max_pe: float = 30):
        self.max_peg = max_peg
        self.min_growth = min_growth
        self.max_pe = max_pe

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        required = ["peg", "growth", "pe"]
        if not all(c in data.columns for c in required):
            return pd.Series(False, index=data.index)

        signals = (
            (data["peg"] < self.max_peg)
            & (data["growth"] > self.min_growth)
            & (data["pe"] < self.max_pe)
        )
        return signals.fillna(False)

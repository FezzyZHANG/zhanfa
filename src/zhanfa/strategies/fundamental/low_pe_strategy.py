"""低市盈率价值策略"""

import pandas as pd

from zhanfa.strategies.base import BaseStrategy


class LowPEStrategy(BaseStrategy):
    """低市盈率价值策略：筛选 PE < max_pe 且 ROE > min_roe 的标的。

    Parameters:
        max_pe: 最大市盈率（默认 15）
        min_roe: 最小 ROE（默认 0.15）
        rebalance_freq: 调仓频率 monthly/quarterly（默认 monthly）
    """

    name = "低市盈率价值策略"

    def __init__(self, max_pe: float = 15, min_roe: float = 0.15, rebalance_freq: str = "monthly"):
        self.max_pe = max_pe
        self.min_roe = min_roe
        self.rebalance_freq = rebalance_freq

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        if "pe" not in data.columns or "roe" not in data.columns:
            return pd.Series(False, index=data.index)

        signals = (data["pe"] < self.max_pe) & (data["roe"] > self.min_roe)
        return signals.fillna(False)

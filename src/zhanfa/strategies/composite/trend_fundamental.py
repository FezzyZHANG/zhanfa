"""趋势+基本面共振策略"""

import pandas as pd

from zhanfa.strategies.base import BaseStrategy
from zhanfa.strategies.indicators import sma


class TrendFundamental(BaseStrategy):
    """趋势+基本面共振策略：均线确认上升趋势后，再以 PE/ROE 筛选标的。

    Parameters:
        ma_period: 均线周期（默认 60）
        max_pe: 最大市盈率（默认 20）
        min_roe: 最小 ROE（默认 0.12）
    """

    name = "趋势+基本面共振策略"

    def __init__(self, ma_period: int = 60, max_pe: float = 20, min_roe: float = 0.12):
        self.ma_period = ma_period
        self.max_pe = max_pe
        self.min_roe = min_roe

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"]
        ma = sma(close, self.ma_period)
        trend_up = close > ma

        has_fundamental = "pe" in data.columns and "roe" in data.columns
        if has_fundamental:
            fundamental_ok = (data["pe"] < self.max_pe) & (data["roe"] > self.min_roe)
        else:
            fundamental_ok = True

        signals = trend_up & fundamental_ok
        return signals.fillna(False)

"""动量+低波多因子策略"""

import pandas as pd

from zhanfa.strategies.base import BaseStrategy


class MomentumLowVol(BaseStrategy):
    """动量+低波多因子策略：综合动量、波动率、质量和规模因子打分选股。

    Parameters:
        top_n: 持仓数量（默认 20）
        factors: 因子列表（默认 ["momentum", "volatility", "quality", "size"]）
    """

    name = "动量+低波多因子策略"

    def __init__(self, top_n: int = 20, factors: list | None = None):
        self.top_n = top_n
        self.factors = factors or ["momentum", "volatility", "quality", "size"]

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"]
        scores = pd.Series(0.0, index=data.index)

        if "momentum" in self.factors:
            mom = close.pct_change(63)  # 3-month momentum
            mom_rank = mom.rank(pct=True)
            scores = scores.add(mom_rank, fill_value=0)

        if "volatility" in self.factors:
            vol = close.pct_change().rolling(21).std()
            vol_rank = (1 - vol.rank(pct=True))  # lower vol = higher score
            scores = scores.add(vol_rank, fill_value=0)

        if "quality" in self.factors:
            if "roe" in data.columns:
                roe_rank = data["roe"].rank(pct=True)
                scores = scores.add(roe_rank, fill_value=0)

        if "size" in self.factors:
            size = close * data.get("volume", pd.Series(1, index=data.index))
            size_rank = size.rank(pct=True)
            scores = scores.add(size_rank, fill_value=0)

        n_active = len([f for f in self.factors if f in ("quality",) and "roe" not in data.columns])
        effective_factors = len(self.factors) - n_active
        if effective_factors > 0:
            scores = scores / effective_factors

        threshold = scores.rank(pct=True) > (1 - self.top_n / max(len(data), self.top_n))
        return threshold.fillna(False)

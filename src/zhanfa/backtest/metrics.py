"""绩效指标计算"""

import numpy as np
import pandas as pd

from zhanfa.config import config


def compute_metrics(
    equity: pd.Series,
    benchmark: pd.Series | None = None,
    risk_free_rate: float | None = None,
) -> dict:
    """从权益曲线计算核心绩效指标。

    Args:
        equity: 权益曲线
        benchmark: 基准（可选，用于超额收益指标）
        risk_free_rate: 年化无风险利率

    Returns:
        dict 包含夏普比率、最大回撤、卡玛比率、年化收益、胜率等
    """
    rf = risk_free_rate if risk_free_rate is not None else config.risk_free_rate
    returns = equity.pct_change().dropna()

    if len(returns) == 0:
        return {
            "total_return": 0.0,
            "ann_return": 0.0,
            "ann_volatility": 0.0,
            "sharpe": 0.0,
            "sortino": 0.0,
            "max_drawdown": 0.0,
            "calmar": 0.0,
            "win_rate": 0.0,
            "years": 0.0,
        }

    total_return = (equity.iloc[-1] / equity.iloc[0]) - 1

    years = _estimate_years(returns)
    ann_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0

    ann_vol = returns.std() * np.sqrt(252)
    sharpe = (ann_return - rf) / ann_vol if ann_vol > 0 else 0

    cummax = equity.expanding().max()
    drawdown = (equity - cummax) / cummax
    max_dd = drawdown.min()
    calmar = ann_return / abs(max_dd) if max_dd != 0 else 0

    win_rate = (returns > 0).mean()

    downside = returns[returns < 0]
    sortino_vol = downside.std() * np.sqrt(252) if len(downside) > 0 else ann_vol
    sortino = (ann_return - rf) / sortino_vol if sortino_vol > 0 else 0

    metrics = {
        "total_return": total_return,
        "ann_return": ann_return,
        "ann_volatility": ann_vol,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown": max_dd,
        "calmar": calmar,
        "win_rate": win_rate,
        "years": years,
    }

    if benchmark is not None:
        bench_return = (benchmark.iloc[-1] / benchmark.iloc[0]) - 1
        bench_ann = (1 + bench_return) ** (1 / years) - 1
        metrics["benchmark_return"] = bench_return
        metrics["excess_return"] = total_return - bench_return
        metrics["ann_excess"] = ann_return - bench_ann

    return metrics


def _estimate_years(returns: pd.Series) -> float:
    """估算回测年数"""
    days = (returns.index[-1] - returns.index[0]).days
    return max(days / 365.25, 0.1)

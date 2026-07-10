"""绩效指标单元测试"""

import numpy as np
import pandas as pd

from zhanfa.backtest.metrics import compute_metrics


def test_compute_metrics_basic():
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=500, freq="B")
    equity = pd.Series(100000 + np.cumsum(np.random.randn(500) * 100), index=dates)

    m = compute_metrics(equity)
    assert "sharpe" in m
    assert "max_drawdown" in m
    assert "calmar" in m
    assert "win_rate" in m
    assert isinstance(m["max_drawdown"], float)
    assert -1 <= m["max_drawdown"] <= 0


def test_compute_metrics_with_benchmark():
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=500, freq="B")
    equity = pd.Series(100000 + np.cumsum(np.random.randn(500) * 100), index=dates)
    bench = pd.Series(100000 + np.cumsum(np.random.randn(500) * 50), index=dates)

    m = compute_metrics(equity, bench)
    assert "excess_return" in m
    assert "ann_excess" in m


def test_compute_metrics_empty_returns():
    """Single-element equity produces empty returns — should return safe zeros, not {}."""
    dates = pd.date_range("2020-01-01", periods=1, freq="B")
    equity = pd.Series([100000.0], index=dates)

    m = compute_metrics(equity)
    # All expected keys should be present with zero values
    expected_keys = [
        "total_return", "ann_return", "ann_volatility",
        "sharpe", "sortino", "max_drawdown", "calmar",
        "win_rate", "years",
    ]
    for key in expected_keys:
        assert key in m, f"Missing key: {key}"
        assert m[key] == 0.0, f"Expected 0.0 for {key}, got {m[key]}"


def test_compute_metrics_zero_vol():
    """Constant equity produces zero volatility — Sharpe & Calmar should be 0."""
    dates = pd.date_range("2020-01-01", periods=100, freq="B")
    equity = pd.Series([100000.0] * 100, index=dates)

    m = compute_metrics(equity)
    assert m["sharpe"] == 0.0
    assert m["ann_volatility"] == 0.0

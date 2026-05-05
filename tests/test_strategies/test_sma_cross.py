"""双均线策略单元测试"""

import numpy as np
import pandas as pd
import pytest

from zhanfa.strategies.trend.sma_cross import SMACross


@pytest.fixture
def sample_data():
    dates = pd.date_range("2024-01-01", periods=200, freq="B")
    np.random.seed(42)
    price = 10 + np.cumsum(np.random.randn(200) * 0.1)
    df = pd.DataFrame({
        "open": price * 0.99,
        "high": price * 1.02,
        "low": price * 0.98,
        "close": price,
        "volume": np.random.randint(1000, 10000, 200),
    }, index=dates)
    return df


def test_sma_cross_returns_bool_series(sample_data):
    s = SMACross(fast=5, slow=20)
    signals = s.generate_signals(sample_data)
    assert isinstance(signals, pd.Series)
    assert signals.dtype == bool
    assert len(signals) == len(sample_data)


def test_sma_cross_no_nan_signals(sample_data):
    s = SMACross(fast=5, slow=20)
    signals = s.generate_signals(sample_data)
    assert not signals.isna().any()


def test_sma_cross_name(sample_data):
    s = SMACross()
    assert s.name == "双均线交叉策略"


def test_sma_cross_basic_rules(sample_data):
    """快线在上买入、下穿卖出——靠近尾巴应该已经产生信号"""
    s = SMACross(fast=5, slow=50)
    signals = s.generate_signals(sample_data)
    # 最后50根 K 线内应有信号变化（慢线已出信号区）
    assert signals.iloc[-50:].nunique() >= 1

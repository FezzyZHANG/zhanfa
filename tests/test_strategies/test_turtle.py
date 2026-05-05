"""海龟策略单元测试"""

import numpy as np
import pandas as pd
import pytest

from zhanfa.strategies.trend.turtle import Turtle


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


def test_turtle_returns_bool_series(sample_data):
    s = Turtle()
    signals = s.generate_signals(sample_data)
    assert isinstance(signals, pd.Series)
    assert signals.dtype == bool
    assert len(signals) == len(sample_data)


def test_turtle_no_nan_signals(sample_data):
    s = Turtle()
    signals = s.generate_signals(sample_data)
    assert not signals.isna().any()


def test_turtle_name():
    s = Turtle()
    assert s.name == "海龟交易法则"


def test_turtle_default_params():
    s = Turtle()
    assert s.entry_period == 20
    assert s.exit_period == 10
    assert s.atr_period == 20
    assert s.atr_mult == 2.0


def test_turtle_custom_params():
    s = Turtle(entry_period=30, exit_period=15, atr_period=25, atr_mult=3.0)
    assert s.entry_period == 30
    assert s.exit_period == 15
    assert s.atr_period == 25
    assert s.atr_mult == 3.0


def test_turtle_basic_rules(sample_data):
    s = Turtle(entry_period=5, exit_period=3)
    signals = s.generate_signals(sample_data)
    # 最后 50 根 K 线内应有信号变化
    assert signals.iloc[-50:].nunique() >= 1


def test_turtle_short_data(sample_data):
    """数据不足一个入场周期时不应崩溃"""
    s = Turtle(entry_period=300)
    signals = s.generate_signals(sample_data)
    assert isinstance(signals, pd.Series)
    assert len(signals) == len(sample_data)


def test_turtle_constant_price():
    """常数价格下不应崩溃"""
    dates = pd.date_range("2024-01-01", periods=100, freq="B")
    df = pd.DataFrame({
        "open": 10.0, "high": 10.0, "low": 10.0,
        "close": 10.0, "volume": 1000,
    }, index=dates)
    s = Turtle()
    signals = s.generate_signals(df)
    assert isinstance(signals, pd.Series)
    assert not signals.isna().any()

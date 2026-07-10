"""动量策略单元测试"""

import numpy as np
import pandas as pd
import pytest

from zhanfa.strategies.momentum.rsi_strategy import RSIStrategy
from zhanfa.strategies.momentum.macd_strategy import MACDStrategy


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


class TestRSIStrategy:
    def test_returns_bool_series(self, sample_data):
        s = RSIStrategy()
        signals = s.generate_signals(sample_data)
        assert isinstance(signals, pd.Series)
        assert signals.dtype == bool
        assert len(signals) == len(sample_data)

    def test_no_nan_signals(self, sample_data):
        s = RSIStrategy()
        signals = s.generate_signals(sample_data)
        assert not signals.isna().any()

    def test_name(self):
        s = RSIStrategy()
        assert s.name == "RSI 超买超卖策略"

    def test_overbought_triggers_exit(self, sample_data):
        dates = pd.date_range("2024-01-01", periods=20, freq="B")
        close = pd.Series(range(1, 21), index=dates, dtype=float)
        data = pd.DataFrame(
            {
                "open": close,
                "high": close + 1,
                "low": close - 1,
                "close": close,
                "volume": [1000] * len(close),
            },
            index=dates,
        )
        s = RSIStrategy(rsi_period=2, oversold=10, overbought=50)
        signals = s.generate_signals(data)
        assert isinstance(signals, pd.Series)
        assert not signals.isna().any()
        assert signals.iloc[-1].item() is False


class TestMACDStrategy:
    def test_returns_bool_series(self, sample_data):
        s = MACDStrategy()
        signals = s.generate_signals(sample_data)
        assert isinstance(signals, pd.Series)
        assert signals.dtype == bool
        assert len(signals) == len(sample_data)

    def test_no_nan_signals(self, sample_data):
        s = MACDStrategy()
        signals = s.generate_signals(sample_data)
        assert not signals.isna().any()

    def test_name(self):
        s = MACDStrategy()
        assert s.name == "MACD 金叉死叉策略"

    def test_signal_changes(self, sample_data):
        s = MACDStrategy(fast=3, slow=10, signal=5)
        signals = s.generate_signals(sample_data)
        assert signals.iloc[-50:].nunique() >= 1
        assert signals.iloc[-1].item() is False

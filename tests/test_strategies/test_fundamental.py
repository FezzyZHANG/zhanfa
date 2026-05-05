"""基本面策略单元测试"""

import numpy as np
import pandas as pd
import pytest

from zhanfa.strategies.fundamental.low_pe_strategy import LowPEStrategy
from zhanfa.strategies.fundamental.peg_strategy import PEGStrategy


@pytest.fixture
def fundamental_data():
    dates = pd.date_range("2024-01-01", periods=20, freq="B")
    np.random.seed(42)
    price = 10 + np.cumsum(np.random.randn(20) * 0.05)
    df = pd.DataFrame({
        "open": price * 0.99,
        "high": price * 1.02,
        "low": price * 0.98,
        "close": price,
        "volume": np.random.randint(1000, 10000, 20),
        "pe": np.linspace(8, 25, 20),
        "roe": np.linspace(0.10, 0.25, 20),
        "peg": np.linspace(0.3, 2.0, 20),
        "growth": np.linspace(0.05, 0.20, 20),
    }, index=dates)
    return df


@pytest.fixture
def ohlcv_data():
    dates = pd.date_range("2024-01-01", periods=100, freq="B")
    np.random.seed(42)
    price = 10 + np.cumsum(np.random.randn(100) * 0.1)
    return pd.DataFrame({
        "open": price * 0.99,
        "high": price * 1.02,
        "low": price * 0.98,
        "close": price,
        "volume": np.random.randint(1000, 10000, 100),
    }, index=dates)


class TestLowPEStrategy:
    def test_returns_bool_series(self, fundamental_data):
        s = LowPEStrategy()
        signals = s.generate_signals(fundamental_data)
        assert isinstance(signals, pd.Series)
        assert signals.dtype == bool
        assert len(signals) == len(fundamental_data)

    def test_no_nan_signals(self, fundamental_data):
        s = LowPEStrategy()
        signals = s.generate_signals(fundamental_data)
        assert not signals.isna().any()

    def test_name(self):
        s = LowPEStrategy()
        assert s.name == "低市盈率价值策略"

    def test_low_pe_high_roe_is_buy(self, fundamental_data):
        s = LowPEStrategy(max_pe=20, min_roe=0.05)
        signals = s.generate_signals(fundamental_data)
        # First row: pe=8, roe=0.10 — should be True (pe < 20 and roe > 0.05)
        assert signals.iloc[0] == True

    def test_high_pe_is_sell(self, fundamental_data):
        s = LowPEStrategy(max_pe=20, min_roe=0.05)
        signals = s.generate_signals(fundamental_data)
        # Last row: pe=25, roe=0.25 — pe > 20 should be False
        assert signals.iloc[-1] == False

    def test_fallback_on_missing_columns(self, ohlcv_data):
        s = LowPEStrategy()
        signals = s.generate_signals(ohlcv_data)
        assert not signals.any()


class TestPEGStrategy:
    def test_returns_bool_series(self, fundamental_data):
        s = PEGStrategy()
        signals = s.generate_signals(fundamental_data)
        assert isinstance(signals, pd.Series)
        assert signals.dtype == bool

    def test_no_nan_signals(self, fundamental_data):
        s = PEGStrategy()
        signals = s.generate_signals(fundamental_data)
        assert not signals.isna().any()

    def test_name(self):
        s = PEGStrategy()
        assert s.name == "彼得·林奇 PEG 策略"

    def test_fallback_on_missing_columns(self, ohlcv_data):
        s = PEGStrategy()
        signals = s.generate_signals(ohlcv_data)
        assert not signals.any()

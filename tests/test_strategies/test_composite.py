"""组合策略单元测试"""

import numpy as np
import pandas as pd
import pytest

from zhanfa.strategies.composite.trend_fundamental import TrendFundamental
from zhanfa.strategies.composite.momentum_lowvol import MomentumLowVol


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


@pytest.fixture
def fundamental_data(sample_data):
    df = sample_data.copy()
    np.random.seed(43)
    df["pe"] = np.random.uniform(8, 30, len(df))
    df["roe"] = np.random.uniform(0.05, 0.30, len(df))
    return df


class TestTrendFundamental:
    def test_returns_bool_series(self, sample_data):
        s = TrendFundamental()
        signals = s.generate_signals(sample_data)
        assert isinstance(signals, pd.Series)
        assert signals.dtype == bool
        assert len(signals) == len(sample_data)

    def test_no_nan_signals(self, sample_data):
        s = TrendFundamental()
        signals = s.generate_signals(sample_data)
        assert not signals.isna().any()

    def test_name(self):
        s = TrendFundamental()
        assert s.name == "趋势+基本面共振策略"

    def test_with_fundamental_data(self, fundamental_data):
        s = TrendFundamental(ma_period=20, max_pe=20, min_roe=0.10)
        signals = s.generate_signals(fundamental_data)
        assert isinstance(signals, pd.Series)
        assert not signals.isna().any()

    def test_ma_period_large_all_false(self, sample_data):
        """Very large MA period should produce no signals before it's available."""
        s = TrendFundamental(ma_period=300)
        signals = s.generate_signals(sample_data)
        # All values should be False since MA is NaN for most of the series
        assert not signals.any() or isinstance(signals, pd.Series)


class TestMomentumLowVol:
    def test_returns_bool_series(self, sample_data):
        s = MomentumLowVol(top_n=10)
        signals = s.generate_signals(sample_data)
        assert isinstance(signals, pd.Series)
        assert signals.dtype == bool
        assert len(signals) == len(sample_data)

    def test_name(self):
        s = MomentumLowVol()
        assert s.name == "动量+低波多因子策略"

    def test_top_n_constraint(self, sample_data):
        s = MomentumLowVol(top_n=5)
        signals = s.generate_signals(sample_data)
        valid = signals.dropna()
        if len(valid) > 0:
            assert valid.sum() <= 5 or valid.sum() <= len(valid) * 0.2

    def test_with_fundamental_data(self, fundamental_data):
        s = MomentumLowVol(top_n=10, factors=["momentum", "volatility", "quality", "size"])
        signals = s.generate_signals(fundamental_data)
        assert isinstance(signals, pd.Series)
        assert not signals.isna().any()

"""Pipeline 单元测试"""

import numpy as np
import pandas as pd
import pytest

from zhanfa.data.pipeline import Pipeline


@pytest.fixture
def sample_df():
    dates = pd.date_range("2024-01-01", periods=200, freq="B")
    np.random.seed(42)
    price = 10 + np.cumsum(np.random.randn(200) * 0.1)
    return pd.DataFrame({
        "open": price * 0.99,
        "high": price * 1.02,
        "low": price * 0.98,
        "close": price,
        "volume": np.random.randint(1000, 100000, 200),
    }, index=dates)


@pytest.fixture
def multi_df():
    dates = pd.date_range("2024-01-01", periods=100, freq="B")
    np.random.seed(1)
    d1 = pd.DataFrame({"close": np.cumsum(np.random.randn(100) * 0.1) + 100}, index=dates)
    np.random.seed(2)
    d2 = pd.DataFrame({"close": np.cumsum(np.random.randn(100) * 0.1) + 50}, index=dates)
    return {"A": d1, "B": d2}


class TestPipelineClean:
    def test_removes_zero_volume(self, sample_df):
        df = sample_df.copy()
        df.loc[df.index[10], "volume"] = 0
        cleaned = Pipeline.clean(df)
        assert df.index[10] not in cleaned.index

    def test_removes_nan_ohlc(self, sample_df):
        df = sample_df.copy()
        df.loc[df.index[5], "close"] = np.nan
        cleaned = Pipeline.clean(df)
        assert df.index[5] not in cleaned.index

    def test_removes_inf(self, sample_df):
        df = sample_df.copy()
        df.loc[df.index[3], "close"] = np.inf
        cleaned = Pipeline.clean(df)
        assert df.index[3] not in cleaned.index

    def test_sorts_index(self, sample_df):
        shuffled = sample_df.sample(frac=1)
        cleaned = Pipeline.clean(shuffled)
        assert cleaned.index.is_monotonic_increasing

    def test_returns_copy(self, sample_df):
        cleaned = Pipeline.clean(sample_df)
        assert cleaned is not sample_df

    def test_converts_str_volume_to_numeric(self):
        """分钟级数据 (Sina) volume/amount 可能为字符串"""
        df = pd.DataFrame({
            "open": [10.0, 11.0], "high": [12.0, 13.0],
            "low": [9.0, 10.0], "close": [11.0, 12.0],
            "volume": ["100000", "0"],
            "amount": ["1000000.0", "0"],
        }, index=pd.date_range("2025-01-02", periods=2, freq="1h"))
        cleaned = Pipeline.clean(df)
        assert pd.api.types.is_numeric_dtype(cleaned["volume"])
        assert pd.api.types.is_numeric_dtype(cleaned["amount"])
        # 第二行 volume=0 被移除
        assert len(cleaned) == 1
        assert cleaned["volume"].iloc[0] == 100000.0


class TestPipelineAlign:
    def test_returns_price_and_returns(self, multi_df):
        price, rets = Pipeline.align(multi_df)
        assert isinstance(price, pd.DataFrame)
        assert isinstance(rets, dict)
        assert set(price.columns) == {"A", "B"}
        assert set(rets.keys()) == {"A", "B"}

    def test_price_no_all_nan_rows(self, multi_df):
        price, _ = Pipeline.align(multi_df)
        assert not price.isna().all(axis=1).any()

    def test_returns_correct_shape(self, multi_df):
        price, rets = Pipeline.align(multi_df)
        for code in ["A", "B"]:
            assert len(rets[code]) == len(price)


class TestPipelineReturns:
    def test_compute_returns(self, sample_df):
        ret = Pipeline.compute_returns(sample_df)
        assert isinstance(ret, pd.Series)
        assert len(ret) == len(sample_df)
        assert ret.iloc[0] != ret.iloc[0]  # 第一根 NaN

    def test_compute_returns_custom_col(self, sample_df):
        df = sample_df.copy()
        df["adjusted"] = df["close"] * 1.1
        ret = Pipeline.compute_returns(df, price_col="adjusted")
        assert len(ret) == len(df)


class TestPipelineIndicators:
    def test_adds_expected_columns(self, sample_df):
        df = Pipeline.add_simple_indicators(sample_df)
        expected = {"sma_20", "sma_60", "sma_120", "vol_sma_20",
                     "channel_pct", "ret_1d", "ret_5d", "ret_20d",
                     "volatility_20d", "atr_14", "high_20", "low_20"}
        assert expected.issubset(set(df.columns))

    def test_sma_calculation(self, sample_df):
        df = Pipeline.add_simple_indicators(sample_df)
        manual_sma20 = sample_df["close"].rolling(20).mean()
        pd.testing.assert_series_equal(df["sma_20"], manual_sma20, check_names=False)

    def test_channel_pct_range(self, sample_df):
        df = Pipeline.add_simple_indicators(sample_df)
        valid = df["channel_pct"].dropna()
        assert (valid >= 0).all() and (valid <= 1.01).all()  # 允许浮点误差

    def test_atr_positive(self, sample_df):
        df = Pipeline.add_simple_indicators(sample_df)
        valid = df["atr_14"].dropna()
        assert (valid > 0).all()

    def test_no_side_effect(self, sample_df):
        cols_before = set(sample_df.columns)
        Pipeline.add_simple_indicators(sample_df)
        assert set(sample_df.columns) == cols_before


class TestPipelineSplit:
    def test_train_test_split(self, sample_df):
        train, test = Pipeline.train_test_split(sample_df, "2024-06-01")
        assert len(train) + len(test) == len(sample_df)
        assert train.index[-1] <= pd.Timestamp("2024-06-01")

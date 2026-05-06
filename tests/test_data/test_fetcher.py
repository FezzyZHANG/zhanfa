"""Fetcher 单元测试（mock akshare 调用）"""

from unittest.mock import patch, MagicMock

import numpy as np
import pandas as pd
import pytest

from zhanfa.data.fetcher import Fetcher
from zhanfa.data.store import Store


@pytest.fixture
def mock_store():
    store = MagicMock(spec=Store)
    store.load.return_value = None
    store.codes.return_value = []
    return store


@pytest.fixture
def mock_ak_daily():
    """模拟 akshare 个股日线返回"""
    dates = pd.date_range("2024-01-01", periods=50, freq="B")
    return pd.DataFrame({
        "日期": dates.strftime("%Y-%m-%d"),
        "开盘": np.random.randn(50).cumsum() + 100,
        "最高": np.random.randn(50).cumsum() + 103,
        "最低": np.random.randn(50).cumsum() + 97,
        "收盘": np.random.randn(50).cumsum() + 100,
        "成交量": np.random.randint(1000, 100000, 50),
        "成交额": np.random.randint(100000, 10000000, 50),
    })


class TestFetcherInit:
    def test_default_store(self):
        f = Fetcher()
        assert isinstance(f.store, Store)

    def test_custom_store(self, mock_store):
        f = Fetcher(store=mock_store)
        assert f.store is mock_store


class TestFetcherDaily:
    def test_returns_cached_when_available(self, mock_store):
        cached = pd.DataFrame({"close": [10, 11]}, index=pd.date_range("2024-01-01", periods=2))
        mock_store.load.return_value = cached
        f = Fetcher(store=mock_store)
        result = f.daily("000001")
        pd.testing.assert_frame_equal(result, cached)
        mock_store.load.assert_called_once_with("000001", "daily", max_age=f.ttl_daily)

    @patch("akshare.stock_zh_a_hist")
    def test_fetches_and_caches_on_miss(self, mock_api, mock_store, mock_ak_daily):
        mock_api.return_value = mock_ak_daily
        f = Fetcher(store=mock_store)
        result = f.daily("000001")

        assert isinstance(result, pd.DataFrame)
        assert "open" in result.columns or "close" in result.columns
        mock_store.save.assert_called_once()
        args = mock_store.save.call_args
        assert args[0][0] == "000001"
        assert args[0][2] == "daily"


class TestFetcherDailyBatch:
    @patch("akshare.stock_zh_a_hist")
    def test_returns_dict_of_dataframes(self, mock_api, mock_store, mock_ak_daily):
        mock_api.return_value = mock_ak_daily
        f = Fetcher(store=mock_store)
        result = f.daily_batch(["000001", "000002"])
        assert isinstance(result, dict)
        assert set(result.keys()) == {"000001", "000002"}
        for df in result.values():
            assert isinstance(df, pd.DataFrame)


class TestFetcherIndexComponents:
    def test_returns_list_of_strings(self, mock_store):
        mock_store.load.return_value = pd.DataFrame({
            "code": ["000001", "000002", "000003"]
        })
        f = Fetcher(store=mock_store)
        result = f.index_components("000300")
        assert result == ["000001", "000002", "000003"]
        mock_store.load.assert_called_once_with("components_000300", "meta", max_age=f.ttl_index_components)


class TestFetcherIndexDaily:
    def test_returns_cached_when_available(self, mock_store):
        """Index daily cache hit returns cached data with correct max_age."""
        cached = pd.DataFrame({"close": [3000, 3010]}, index=pd.date_range("2024-01-01", periods=2))
        mock_store.load.return_value = cached
        f = Fetcher(store=mock_store)
        result = f.index_daily("000300")
        pd.testing.assert_frame_equal(result, cached)
        mock_store.load.assert_called_once_with("000300", "index_daily", max_age=f.ttl_index_daily)


class TestFetcherStockList:
    def test_returns_cached_when_available(self, mock_store):
        """Stock list cache hit returns cached data with correct max_age."""
        # Needs >= 5000 rows to pass truncation check
        cached = pd.DataFrame({
            "code": [f"{i:06d}" for i in range(5000)],
            "name": [f"Stock{i}" for i in range(5000)],
        })
        mock_store.load.return_value = cached
        f = Fetcher(store=mock_store)
        result = f.stock_list()
        pd.testing.assert_frame_equal(result, cached)
        mock_store.load.assert_called_once_with("stock_list", "meta", max_age=f.ttl_stock_list)

    @patch("akshare.stock_info_a_code_name")
    def test_returns_df_with_code_name(self, mock_api, mock_store):
        mock_api.return_value = pd.DataFrame({
            "code": ["000001", "000002"],
            "name": ["平安银行", "万科A"]
        })
        mock_store.load.return_value = None
        f = Fetcher(store=mock_store)
        result = f.stock_list()
        assert list(result.columns) == ["code", "name"]


class TestFetcherFinancial:
    def test_returns_cached_when_available(self, mock_store):
        """Financial cache hit returns cached data with correct max_age."""
        cached = pd.DataFrame({"net_profit": [100, 200]}, index=[0, 1])
        mock_store.load.return_value = cached
        f = Fetcher(store=mock_store)
        result = f.financial("000001")
        pd.testing.assert_frame_equal(result, cached)
        mock_store.load.assert_called_once_with("000001", "financial", max_age=f.ttl_financial)


class TestFetcherCleanOHLCV:
    def test_renames_columns(self):
        f = Fetcher()
        df = pd.DataFrame({
            "日期": ["2024-01-01", "2024-01-02"],
            "开盘": [10.0, 11.0],
            "收盘": [11.0, 12.0],
            "成交量": [1000, 2000],
        })
        result = f._clean_ohlcv(df)
        assert "date" not in result.columns
        assert isinstance(result.index, pd.DatetimeIndex)
        assert result.index.name is None

    def test_sorts_index(self):
        f = Fetcher()
        df = pd.DataFrame({
            "日期": ["2024-01-05", "2024-01-01"],
            "开盘": [11.0, 10.0],
            "收盘": [12.0, 11.0],
            "成交量": [2000, 1000],
        })
        result = f._clean_ohlcv(df)
        assert result.index.is_monotonic_increasing


class TestFetcherMinute:
    """分钟级数据获取测试"""

    def test_to_sina_code_sh(self):
        assert Fetcher._to_sina_code("600519") == "sh600519"
        assert Fetcher._to_sina_code("688001") == "sh688001"

    def test_to_sina_code_sz(self):
        assert Fetcher._to_sina_code("000001") == "sz000001"
        assert Fetcher._to_sina_code("300750") == "sz300750"

    def test_clean_minute_converts_str_volume(self):
        df = pd.DataFrame({
            "day": ["2025-01-02 09:45:00", "2025-01-02 10:00:00"],
            "open": [10.0, 11.0],
            "high": [11.0, 12.0],
            "low": [9.5, 10.5],
            "close": [10.5, 11.5],
            "volume": ["100000", "200000"],
            "amount": ["1050000.0", "2300000.0"],
        })
        result = Fetcher._clean_minute(df)
        assert pd.api.types.is_numeric_dtype(result["volume"])
        assert pd.api.types.is_numeric_dtype(result["amount"])
        assert result["volume"].iloc[0] == 100000.0
        assert result["amount"].iloc[1] == 2300000.0

    def test_clean_minute_sets_datetime_index(self):
        df = pd.DataFrame({
            "day": ["2025-01-02 09:45:00", "2025-01-02 10:00:00"],
            "open": [10.0, 11.0], "high": [11.0, 12.0],
            "low": [9.5, 10.5], "close": [10.5, 11.5],
            "volume": ["1000", "2000"], "amount": ["1e6", "2e6"],
        })
        result = Fetcher._clean_minute(df)
        assert isinstance(result.index, pd.DatetimeIndex)
        assert "date" not in result.columns
        assert result.index.is_monotonic_increasing

    def test_clean_minute_handles_mixed_types(self):
        """volume 已是数值时不报错"""
        df = pd.DataFrame({
            "day": ["2025-01-02 09:45:00"],
            "open": [10.0], "high": [11.0], "low": [9.0], "close": [10.5],
            "volume": [100000],
            "amount": [1e6],
        })
        result = Fetcher._clean_minute(df)
        assert result["volume"].iloc[0] == 100000

    @patch("akshare.stock_zh_a_minute")
    def test_minute_fetches_and_caches(self, mock_api, mock_store):
        mock_api.return_value = pd.DataFrame({
            "day": ["2025-01-02 10:00:00", "2025-01-02 10:15:00"],
            "open": [10.0, 11.0], "high": [11.0, 12.0],
            "low": [9.5, 10.5], "close": [10.5, 11.5],
            "volume": ["1000", "2000"], "amount": ["1e6", "2e6"],
        })
        f = Fetcher(store=mock_store)
        result = f.minute("000001", period="60")
        assert isinstance(result, pd.DataFrame)
        mock_store.save.assert_called_once()
        args = mock_store.save.call_args
        assert args[0][0] == "000001"
        assert args[0][2] == "minute_60"

    def test_minute_returns_cached(self, mock_store):
        cached = pd.DataFrame(
            {"close": [10, 11]},
            index=pd.date_range("2025-01-02", periods=2, freq="1h")
        )
        mock_store.load.return_value = cached
        f = Fetcher(store=mock_store)
        result = f.minute("000001", period="60")
        pd.testing.assert_frame_equal(result, cached)
        mock_store.load.assert_called_once_with("000001", "minute_60", max_age=f.ttl_minute)

    @patch("akshare.stock_zh_a_minute")
    def test_minute_batch(self, mock_api, mock_store):
        mock_api.return_value = pd.DataFrame({
            "day": ["2025-01-02 10:00:00"],
            "open": [10.0], "high": [11.0], "low": [9.0], "close": [10.5],
            "volume": ["1000"], "amount": ["1e6"],
        })
        f = Fetcher(store=mock_store)
        result = f.minute_batch(["000001", "000002"], period="15")
        assert isinstance(result, dict)
        assert set(result.keys()) == {"000001", "000002"}

"""Fetcher TTL & cache integrity tests."""

import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from zhanfa.data.fetcher import Fetcher, _env_ttl
from zhanfa.data.store import Store


class TestEnvTTL:
    def test_returns_timedelta_from_env(self, monkeypatch):
        monkeypatch.setenv("CACHE_TTL_DAILY_HOURS", "2")
        result = _env_ttl("CACHE_TTL_DAILY_HOURS", 6)
        assert result == timedelta(hours=2)

    def test_falls_back_to_default(self, monkeypatch):
        monkeypatch.delenv("CACHE_TTL_DAILY_HOURS", raising=False)
        result = _env_ttl("CACHE_TTL_DAILY_HOURS", 6)
        assert result == timedelta(hours=6)

    def test_returns_none_when_both_unset(self, monkeypatch):
        monkeypatch.delenv("CACHE_TTL_UNKNOWN", raising=False)
        result = _env_ttl("CACHE_TTL_UNKNOWN", None)
        assert result is None

    def test_invalid_env_uses_default(self, monkeypatch):
        monkeypatch.setenv("CACHE_TTL_DAILY_HOURS", "not_a_number")
        result = _env_ttl("CACHE_TTL_DAILY_HOURS", 6)
        assert result == timedelta(hours=6)


class TestFetcherTTL:
    def test_fetcher_has_ttl_attributes(self):
        f = Fetcher()
        assert f.ttl_daily == timedelta(hours=6)
        assert f.ttl_index_daily == timedelta(hours=6)
        assert f.ttl_stock_list == timedelta(hours=24)
        assert f.ttl_index_components == timedelta(hours=24)
        assert f.ttl_industry_stocks == timedelta(hours=24)
        assert f.ttl_financial == timedelta(hours=720)  # ~30 days
        assert f.ttl_minute == timedelta(hours=6)

    def test_ttl_from_env_override(self, monkeypatch):
        monkeypatch.setenv("CACHE_TTL_DAILY_HOURS", "1")
        f = Fetcher()
        assert f.ttl_daily == timedelta(hours=1)


class TestCacheIntegrityDaily:
    """Phase 4: cache integrity validation — bad cache auto-delete and re-fetch."""

    @patch("akshare.stock_zh_a_hist")
    def test_deletes_truncated_daily_and_re_fetches(self, mock_api):
        """When daily cache has < 1 row, delete it and re-fetch."""
        mock_api.return_value = pd.DataFrame({
            "日期": ["2024-01-01", "2024-01-02"],
            "开盘": [10.0, 11.0], "最高": [12.0, 13.0],
            "最低": [9.0, 10.0], "收盘": [11.0, 12.0],
            "成交量": [1000, 2000],
        })

        mock_store = MagicMock(spec=Store)
        # First load returns empty df (bad cache — needs fixing)
        empty_df = pd.DataFrame(columns=["close"])
        mock_store.load.return_value = empty_df
        # After delete, re-fetch happens

        f = Fetcher(store=mock_store)
        result = f.daily("000001")
        assert len(result) == 2
        # Should delete the bad cache before re-fetch
        mock_store.delete.assert_called_once_with("000001", "daily")

    @patch("akshare.stock_zh_a_hist")
    def test_skips_delete_when_cached_has_data(self, mock_api):
        """When cached data is valid (>= 1 row), don't delete."""
        mock_store = MagicMock(spec=Store)
        valid_df = pd.DataFrame(
            {"close": [10.0, 11.0]},
            index=pd.date_range("2024-01-01", periods=2)
        )
        mock_store.load.return_value = valid_df

        f = Fetcher(store=mock_store)
        result = f.daily("000001")
        assert len(result) == 2
        mock_store.delete.assert_not_called()


class TestCacheIntegrityStockList:
    """stock_list cache integrity: >= 5000 rows required."""

    @patch("akshare.stock_info_a_code_name")
    def test_deletes_truncated_stock_list(self, mock_api):
        """When stock_list cache has < 5000 rows, delete and re-fetch."""
        codes = [str(i).zfill(6) for i in range(1, 5001)]
        mock_api.return_value = pd.DataFrame({
            "code": codes,
            "name": [f"Stock{i}" for i in codes],
        })

        mock_store = MagicMock(spec=Store)
        # Return truncated cache (only 2 rows — mimics the known bug)
        truncated = pd.DataFrame({
            "code": ["000001", "000002"],
            "name": ["平安银行", "万科A"],
        })
        mock_store.load.return_value = truncated

        f = Fetcher(store=mock_store)
        result = f.stock_list()
        assert len(result) >= 5000
        mock_store.delete.assert_called_once_with("stock_list", "meta")

    @patch("akshare.stock_info_a_code_name")
    def test_accepts_valid_stock_list(self, mock_api):
        """When stock_list has >= 5000 rows, use it as-is."""
        mock_store = MagicMock(spec=Store)
        codes = [str(i).zfill(6) for i in range(1, 5001)]
        valid = pd.DataFrame({
            "code": codes,
            "name": [f"Stock{i}" for i in codes],
        })
        mock_store.load.return_value = valid

        f = Fetcher(store=mock_store)
        result = f.stock_list()
        assert len(result) >= 5000
        mock_store.delete.assert_not_called()
        # Should NOT call the API since cache is valid
        mock_api.assert_not_called()

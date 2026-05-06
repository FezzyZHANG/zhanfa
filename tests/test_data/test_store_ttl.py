"""Store TTL & mtime tests."""

import os
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

from zhanfa.data.store import Store


def make_daily_parquet(base: Path, code: str = "000001") -> Path:
    (base / "daily").mkdir(parents=True, exist_ok=True)
    dates = pd.date_range("2024-01-01", periods=5, freq="B")
    df = pd.DataFrame({"close": [10.0, 11.0, 12.0, 13.0, 14.0]}, index=dates)
    path = base / "daily" / f"{code}.parquet"
    df.to_parquet(path, index=True)
    return path


class TestStoreMtime:
    def test_mtime_returns_datetime(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            path = make_daily_parquet(base, "000001")
            store = Store(str(base))
            mtime = store.mtime("000001", "daily")
            assert isinstance(mtime, datetime)
            assert mtime.tzinfo is not None  # UTC

    def test_mtime_none_for_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(str(tmp))
            assert store.mtime("nonexistent", "daily") is None

    def test_mtime_none_for_nonexistent_dir(self):
        store = Store("/nonexistent_path_xyz")
        assert store.mtime("000001", "daily") is None

    def test_mtime_updates_after_save(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            store = Store(str(base))
            path = make_daily_parquet(base, "000001")
            mtime1 = store.mtime("000001", "daily")
            time.sleep(0.1)
            # Touch the file
            os.utime(path, None)
            mtime2 = store.mtime("000001", "daily")
            assert mtime2 >= mtime1


class TestStoreLoadMaxAge:
    def test_load_returns_data_within_ttl(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            make_daily_parquet(base, "000001")
            store = Store(str(base))
            df = store.load("000001", "daily", max_age=timedelta(hours=1))
            assert df is not None
            assert len(df) == 5

    def test_load_returns_none_when_expired(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            path = make_daily_parquet(base, "000001")
            # Set mtime to 2 hours ago
            old_time = (datetime.now(timezone.utc) - timedelta(hours=2)).timestamp()
            os.utime(path, (old_time, old_time))
            store = Store(str(base))
            df = store.load("000001", "daily", max_age=timedelta(hours=1))
            assert df is None

    def test_load_without_max_age_returns_always(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            path = make_daily_parquet(base, "000001")
            old_time = (datetime.now(timezone.utc) - timedelta(hours=2)).timestamp()
            os.utime(path, (old_time, old_time))
            store = Store(str(base))
            df = store.load("000001", "daily")  # no max_age
            assert df is not None

    def test_load_returns_none_for_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(str(tmp))
            assert store.load("nonexistent", "daily", max_age=timedelta(hours=1)) is None


class TestStoreStatsLastRefreshed:
    def test_stats_includes_last_refreshed_at(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            make_daily_parquet(base, "000001")
            store = Store(str(base))
            stats = store.stats()
            assert "last_refreshed_at" in stats
            assert stats["last_refreshed_at"] is not None

    def test_stats_last_refreshed_at_none_for_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(str(tmp))
            stats = store.stats()
            assert stats["last_refreshed_at"] is None

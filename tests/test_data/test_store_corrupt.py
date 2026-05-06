"""Store 损坏缓存降级测试"""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from zhanfa.data.store import Store


@pytest.fixture
def store():
    with tempfile.TemporaryDirectory() as tmp:
        yield Store(base_dir=tmp)


@pytest.fixture
def sample_df():
    dates = pd.date_range("2024-01-01", periods=100, freq="B")
    return pd.DataFrame({
        "open": [100.0 + i * 0.1 for i in range(100)],
        "high": [102.0 + i * 0.1 for i in range(100)],
        "low": [98.0 + i * 0.1 for i in range(100)],
        "close": [100.0 + i * 0.1 for i in range(100)],
        "volume": [10000 + i * 10 for i in range(100)],
    }, index=dates)


class TestCorruptedParquet:
    def test_load_corrupted_returns_none(self, store, sample_df):
        """Loading a corrupted parquet file should return None."""
        store.save("TEST001", sample_df, "daily")
        path = store._path("TEST001", "daily")
        # Write garbage over the file
        path.write_bytes(b"this is not a parquet file")

        result = store.load("TEST001", "daily")
        assert result is None

    def test_load_partial_truncated_returns_none(self, store, sample_df):
        """Loading a truncated parquet returns None gracefully."""
        store.save("TEST001", sample_df, "daily")
        path = store._path("TEST001", "daily")
        # Truncate to 10 bytes
        path.write_bytes(path.read_bytes()[:10])

        result = store.load("TEST001", "daily")
        assert result is None

    def test_exists_corrupted_still_true(self, store, sample_df):
        """exists() should still return True even if parquet is corrupted."""
        store.save("TEST001", sample_df, "daily")
        path = store._path("TEST001", "daily")
        path.write_bytes(b"garbage")

        assert store.exists("TEST001", "daily") is True

    def test_mtime_corrupted_still_works(self, store, sample_df):
        """mtime() should still return a timestamp for corrupted files."""
        store.save("TEST001", sample_df, "daily")
        path = store._path("TEST001", "daily")
        path.write_bytes(b"garbage")

        mtime = store.mtime("TEST001", "daily")
        assert mtime is not None

    def test_save_overwrites_corrupted(self, store, sample_df):
        """Saving after corruption replaces the broken file."""
        store.save("TEST001", sample_df, "daily")
        path = store._path("TEST001", "daily")
        path.write_bytes(b"garbage")

        store.save("TEST001", sample_df, "daily")
        result = store.load("TEST001", "daily")
        assert result is not None
        assert len(result) == 100

    def test_stats_excludes_corrupted_from_row_count(self, store, sample_df):
        """Stats should not count corrupted file rows."""
        store.save("TEST001", sample_df, "daily")
        path = store._path("TEST001", "daily")
        path.write_bytes(b"garbage")

        stats = store.stats()
        # stock_count still = 1 (file exists)
        assert stats["stock_count"] == 1
        # But corrupted file contributes 0 rows (not countable)
        assert stats["total_rows"] == 0

"""Store 单元测试"""

import tempfile

import numpy as np
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
        "open": np.random.randn(100).cumsum() + 100,
        "high": np.random.randn(100).cumsum() + 102,
        "low": np.random.randn(100).cumsum() + 98,
        "close": np.random.randn(100).cumsum() + 100,
        "volume": np.random.randint(1000, 100000, 100),
    }, index=dates)


def _assert_frame_equal(a, b):
    """parquet 往返不保留 DatetimeIndex.freq，比较前统一去除"""
    a = a.copy()
    b = b.copy()
    if isinstance(a.index, pd.DatetimeIndex):
        a.index.freq = None
    if isinstance(b.index, pd.DatetimeIndex):
        b.index.freq = None
    pd.testing.assert_frame_equal(a, b)


class TestStore:
    def test_save_and_load(self, store, sample_df):
        store.save("000001", sample_df)
        loaded = store.load("000001")
        assert loaded is not None
        _assert_frame_equal(sample_df, loaded)

    def test_load_nonexistent(self, store):
        assert store.load("nonexistent") is None

    def test_exists(self, store, sample_df):
        assert not store.exists("000001")
        store.save("000001", sample_df)
        assert store.exists("000001")

    def test_codes(self, store, sample_df):
        store.save("000001", sample_df)
        store.save("000002", sample_df)
        codes = store.codes()
        assert set(codes) == {"000001", "000002"}

    def test_codes_empty(self, store):
        assert store.codes() == []

    def test_codes_empty_dir(self, store):
        assert store.codes("weekly") == []

    def test_save_batch(self, store, sample_df):
        data = {"A": sample_df, "B": sample_df}
        store.save_batch(data)
        assert store.exists("A")
        assert store.exists("B")

    def test_different_freq(self, store, sample_df):
        store.save("000001", sample_df, freq="weekly")
        assert store.exists("000001", "weekly")
        assert not store.exists("000001", "daily")
        loaded = store.load("000001", "weekly")
        _assert_frame_equal(sample_df, loaded)

    def test_overwrite(self, store, sample_df):
        store.save("000001", sample_df)
        modified = sample_df.copy()
        modified["close"] = modified["close"] + 10
        store.save("000001", modified)
        loaded = store.load("000001")
        _assert_frame_equal(modified, loaded)

    def test_file_path(self, store):
        expected = store.base / "daily" / "000001.parquet"
        assert store._path("000001") == expected

    @pytest.mark.parametrize(
        ("code", "freq"),
        [
            ("../000001", "daily"),
            ("000001/../../x", "daily"),
            ("000001", "../daily"),
            ("000001", "daily\\..\\x"),
        ],
    )
    def test_rejects_path_traversal(self, store, code, freq):
        with pytest.raises(ValueError, match="Invalid cache"):
            store._path(code, freq)

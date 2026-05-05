"""Data API endpoint tests — stats, stock-status, refresh."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
# ── Stats ────────────────────────────────────────────────


def test_stats_structure(client):
    r = client.get("/api/data/stats")
    assert r.status_code == 200
    data = r.json()
    assert "cache" in data
    assert "database" in data
    cache = data["cache"]
    assert "stock_count" in cache
    assert "total_rows" in cache
    assert "storage_bytes" in cache
    assert "date_range_start" in cache
    assert "date_range_end" in cache
    assert "freq_stats" in cache
    db = data["database"]
    assert "stock_count" in db
    assert "financial_count" in db
    assert "watchlist_count" in db
    assert "strategy_count" in db
    assert "backtest_count" in db


def test_stats_empty_cache(client):
    with patch("zhanfa.api.routers.data.Store") as MockStore:
        mock = MockStore.return_value
        mock.stats.return_value = {
            "stock_count": 0,
            "total_rows": 0,
            "storage_bytes": 0,
            "date_range": {"start": None, "end": None},
            "freq_stats": {},
        }
        r = client.get("/api/data/stats")
        assert r.status_code == 200
        data = r.json()
        assert data["cache"]["stock_count"] == 0
        assert data["cache"]["date_range_start"] is None


# ── Stock Status ─────────────────────────────────────────


def test_stock_status_with_cached_data(client):
    from zhanfa.data.store import Store

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)

        # Create daily data
        (base / "daily").mkdir()
        dates = pd.date_range("2024-01-01", periods=50, freq="B")
        df = pd.DataFrame(
            {"open": 10.0, "high": 11.0, "low": 9.0, "close": 10.5, "volume": 10000},
            index=dates,
        )
        df.to_parquet(base / "daily" / "000001.parquet", index=True)

        # Create stock_list meta
        (base / "meta").mkdir()
        sl = pd.DataFrame({"code": ["000001"], "name": ["平安银行"]})
        sl.to_parquet(base / "meta" / "stock_list.parquet", index=False)

        real = Store(str(tmp))
        with patch("zhanfa.api.routers.data.Store", return_value=real):
            r = client.get("/api/data/stock-status?code=000001")
            assert r.status_code == 200
            data = r.json()
            assert data["code"] == "000001"
            assert data["has_daily"] is True
            assert data["daily_start"] == "2024-01-01"
            assert data["daily_end"] == "2024-03-08"
            assert data["daily_rows"] == 50
            assert data["has_financial"] is False


def test_stock_status_nonexistent(client):
    from zhanfa.data.store import Store

    with tempfile.TemporaryDirectory() as tmp:
        real = Store(str(tmp))
        with patch("zhanfa.api.routers.data.Store", return_value=real):
            r = client.get("/api/data/stock-status?code=nonexistent")
            assert r.status_code == 200
            data = r.json()
            assert data["code"] == "nonexistent"
            assert data["has_daily"] is False
            assert data["has_financial"] is False
            assert data["in_watchlist"] == []


# ── Refresh ──────────────────────────────────────────────


def test_refresh_incremental(client):
    mock_fetcher = MagicMock()
    mock_fetcher.daily.return_value = pd.DataFrame({"close": [10.0, 11.0]})
    mock_fetcher.stock_list.return_value = pd.DataFrame(
        {"code": ["000001"], "name": ["平安银行"]}
    )

    with patch("zhanfa.automation.workflows.Fetcher", return_value=mock_fetcher):
        r = client.post(
            "/api/data/refresh",
            json={"codes": ["000001", "600519"], "freq": "daily", "force": False},
        )
    assert r.status_code == 200
    data = r.json()
    assert data["updated"] == 2
    assert data["failed"] == 0

    stats = client.get("/api/data/stats").json()
    assert stats["database"]["stock_count"] >= 1


def test_refresh_force_deletes_then_fetches(client):
    """Force refresh should delete existing cache files and re-fetch."""
    from zhanfa.data.store import Store

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        (base / "daily").mkdir()
        dates = pd.date_range("2024-01-01", periods=10, freq="B")
        df = pd.DataFrame({"close": 1.0}, index=dates)
        df.to_parquet(base / "daily" / "000001.parquet", index=True)

        mock_fetcher = MagicMock()
        mock_fetcher.daily.return_value = pd.DataFrame({"close": [20.0, 21.0]})
        mock_fetcher.stock_list.return_value = pd.DataFrame(
            {"code": ["000001"], "name": ["test"]}
        )

        real_store = Store(str(tmp))
        with patch("zhanfa.api.routers.data.Store", return_value=real_store):
            with patch(
                "zhanfa.automation.workflows.Fetcher", return_value=mock_fetcher
            ):
                r = client.post(
                    "/api/data/refresh",
                    json={"codes": ["000001"], "freq": "daily", "force": True},
                )
            assert r.status_code == 200
            data = r.json()
            assert data["updated"] == 1


def test_refresh_handles_failure(client):
    mock_fetcher = MagicMock()
    mock_fetcher.stock_list.return_value = pd.DataFrame(
        {"code": ["000001"], "name": ["test"]}
    )

    def side_effect(code):
        if code == "bad_code":
            raise RuntimeError("fail")
        return pd.DataFrame({"close": [1.0]})

    mock_fetcher.daily.side_effect = side_effect

    with patch("zhanfa.automation.workflows.Fetcher", return_value=mock_fetcher):
        r = client.post(
            "/api/data/refresh",
            json={"codes": ["000001", "bad_code"], "freq": "daily", "force": False},
        )
    assert r.status_code == 200
    data = r.json()
    assert data["updated"] == 1
    assert data["failed"] == 1
    assert len(data["errors"]) == 1
    assert data["errors"][0]["code"] == "bad_code"


def test_refresh_minute_15_calls_fetcher_minute(client):
    """freq=minute_15 should call Fetcher.minute(code, period='15')."""
    mock_fetcher = MagicMock()
    mock_fetcher.minute.return_value = pd.DataFrame({"close": [10.0, 11.0]})

    with patch("zhanfa.automation.workflows.Fetcher", return_value=mock_fetcher):
        r = client.post(
            "/api/data/refresh",
            json={"codes": ["000001"], "freq": "minute_15", "force": False},
        )
    assert r.status_code == 200
    data = r.json()
    assert data["updated"] == 1
    assert data["failed"] == 0
    mock_fetcher.minute.assert_called_once_with("000001", period="15")


def test_refresh_minute_60_calls_fetcher_minute(client):
    """freq=minute_60 should call Fetcher.minute(code, period='60')."""
    mock_fetcher = MagicMock()
    mock_fetcher.minute.return_value = pd.DataFrame({"close": [5.0]})

    with patch("zhanfa.automation.workflows.Fetcher", return_value=mock_fetcher):
        r = client.post(
            "/api/data/refresh",
            json={"codes": ["600519"], "freq": "minute_60", "force": False},
        )
    assert r.status_code == 200
    assert r.json()["updated"] == 1
    mock_fetcher.minute.assert_called_once_with("600519", period="60")


def test_refresh_minute_force_deletes_and_fetches_target_freq(client):
    """Force refresh with minute_30 should delete minute_30 cache and re-fetch."""
    from zhanfa.data.store import Store

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        (base / "minute_30").mkdir()
        dates = pd.date_range("2024-01-01", periods=5, freq="h")
        df = pd.DataFrame({"close": 1.0}, index=dates)
        df.to_parquet(base / "minute_30" / "000001.parquet", index=True)

        mock_fetcher = MagicMock()
        mock_fetcher.minute.return_value = pd.DataFrame({"close": [20.0, 21.0]})

        real_store = Store(str(tmp))
        # Verify cache exists before refresh
        assert real_store.exists("000001", "minute_30")

        with patch("zhanfa.api.routers.data.Store", return_value=real_store):
            with patch(
                "zhanfa.automation.workflows.Fetcher", return_value=mock_fetcher
            ):
                r = client.post(
                    "/api/data/refresh",
                    json={"codes": ["000001"], "freq": "minute_30", "force": True},
                )
            assert r.status_code == 200
            data = r.json()
            assert data["updated"] == 1

            # Cache should be deleted (force) and then re-fetched
            mock_fetcher.minute.assert_called_once_with("000001", period="30")
            # daily() should NOT be called
            mock_fetcher.daily.assert_not_called()


def test_refresh_invalid_freq_returns_400(client):
    """Unknown freq should return 400 with a clear error message."""
    r = client.post(
        "/api/data/refresh",
        json={"codes": ["000001"], "freq": "weekly", "force": False},
    )
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert "未知频率" in detail
    assert "weekly" in detail



# ── OpenAPI ──────────────────────────────────────────────


def test_data_endpoints_in_openapi(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    schema = r.json()
    paths = schema["paths"]
    assert "/api/data/stats" in paths
    assert "/api/data/stock-status" in paths
    assert "/api/data/refresh" in paths

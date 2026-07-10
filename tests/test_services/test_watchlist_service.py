"""Watchlist service tests."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from zhanfa.db.models import Stock
from zhanfa.api.services.watchlist_service import (
    list_watchlists,
    create_watchlist,
    get_watchlist,
    update_watchlist,
    delete_watchlist,
    add_item,
    remove_item,
    update_item_notes,
    batch_add_items,
    batch_move_items,
    export_csv,
    DEFAULT_WL_NAME,
)


@pytest.fixture
def db_with_stock(db_session):
    """DB session with a stock pre-inserted."""
    db_session.add(Stock(code="000001", name="平安银行", exchange="SZ"))
    db_session.add(Stock(code="600519", name="贵州茅台", exchange="SH"))
    db_session.commit()
    return db_session


class TestListWatchlists:
    def test_creates_default_if_empty(self, db_session):
        result = list_watchlists(db_session)
        assert len(result) == 1
        assert result[0]["name"] == DEFAULT_WL_NAME

    def test_does_not_duplicate_default(self, db_session):
        list_watchlists(db_session)
        list_watchlists(db_session)
        result = list_watchlists(db_session)
        assert len(result) == 1


class TestCreateWatchlist:
    def test_creates_new(self, db_session):
        wl = create_watchlist(db_session, "My List")
        assert wl["name"] == "My List"
        assert wl["stock_count"] == 0
        assert "id" in wl


class TestGetWatchlist:
    def test_returns_watchlist(self, db_session):
        wl = create_watchlist(db_session, "Test")
        result = get_watchlist(db_session, wl["id"])
        assert result["name"] == "Test"

    def test_returns_none_for_missing(self, db_session):
        assert get_watchlist(db_session, 99999) is None


class TestUpdateWatchlist:
    def test_updates_name(self, db_session):
        wl = create_watchlist(db_session, "Old")
        result = update_watchlist(db_session, wl["id"], "New")
        assert result["name"] == "New"

    def test_returns_none_for_missing(self, db_session):
        assert update_watchlist(db_session, 99999, "X") is None


class TestDeleteWatchlist:
    def test_deletes_watchlist(self, db_session):
        wl = create_watchlist(db_session, "ToDelete")
        ok, msg = delete_watchlist(db_session, wl["id"])
        assert ok
        assert get_watchlist(db_session, wl["id"]) is None

    def test_cannot_delete_default(self, db_session):
        list_watchlists(db_session)  # ensure default exists
        wl = get_watchlist(db_session, 1)
        ok, msg = delete_watchlist(db_session, wl["id"])
        assert not ok
        assert "默认" in msg

    def test_returns_false_for_missing(self, db_session):
        ok, msg = delete_watchlist(db_session, 99999)
        assert not ok


class TestAddItem:
    def test_adds_item(self, db_with_stock):
        wl = create_watchlist(db_with_stock, "Test")
        result = add_item(db_with_stock, wl["id"], "000001")
        assert "000001" in result["items"][0]["code"]

    def test_no_duplicate(self, db_with_stock):
        wl = create_watchlist(db_with_stock, "Test")
        add_item(db_with_stock, wl["id"], "000001")
        result = add_item(db_with_stock, wl["id"], "000001")
        assert len([i for i in result["items"] if i["code"] == "000001"]) == 1

    def test_returns_none_for_missing_wl(self, db_session):
        assert add_item(db_session, 99999, "000001") is None

    def test_creates_missing_stock_before_add(self, db_session):
        wl = create_watchlist(db_session, "Test")
        mock_fetcher = MagicMock()
        mock_fetcher.stock_list.return_value = pd.DataFrame({
            "code": ["000001"],
            "name": ["平安银行"],
        })

        with patch("zhanfa.api.services.watchlist_service.Fetcher", return_value=mock_fetcher):
            result = add_item(db_session, wl["id"], "1")

        assert any(item["code"] == "000001" for item in result["items"])
        stock = db_session.get(Stock, "000001")
        assert stock is not None
        assert stock.name == "平安银行"


class TestRemoveItem:
    def test_removes_item(self, db_with_stock):
        wl = create_watchlist(db_with_stock, "Test")
        add_item(db_with_stock, wl["id"], "000001")
        assert remove_item(db_with_stock, wl["id"], "000001")
        result = get_watchlist(db_with_stock, wl["id"])
        assert len(result["items"]) == 0

    def test_returns_false_for_missing(self, db_session):
        assert not remove_item(db_session, 99999, "000001")


class TestUpdateItemNotes:
    def test_updates_notes(self, db_with_stock):
        wl = create_watchlist(db_with_stock, "Test")
        add_item(db_with_stock, wl["id"], "000001", notes="old")
        result = update_item_notes(db_with_stock, wl["id"], "000001", "new")
        item = [i for i in result["items"] if i["code"] == "000001"][0]
        assert item["notes"] == "new"

    def test_returns_none_for_missing_wl(self, db_session):
        assert update_item_notes(db_session, 99999, "000001", "x") is None

    def test_returns_none_for_missing_code(self, db_with_stock):
        wl = create_watchlist(db_with_stock, "Test")
        assert update_item_notes(db_with_stock, wl["id"], "600519", "x") is None


class TestBatchAddItems:
    def test_adds_multiple(self, db_with_stock):
        wl = create_watchlist(db_with_stock, "Test")
        result = batch_add_items(db_with_stock, wl["id"], ["000001", "600519"])
        codes = [i["code"] for i in result["items"]]
        assert "000001" in codes
        assert "600519" in codes

    def test_deduplicates(self, db_with_stock):
        wl = create_watchlist(db_with_stock, "Test")
        add_item(db_with_stock, wl["id"], "000001")
        result = batch_add_items(db_with_stock, wl["id"], ["000001", "600519"])
        assert len(result["items"]) == 2

    def test_returns_none_for_missing_wl(self, db_session):
        assert batch_add_items(db_session, 99999, ["000001"]) is None

    def test_creates_missing_stocks_before_batch_add(self, db_session):
        wl = create_watchlist(db_session, "Test")
        mock_fetcher = MagicMock()
        mock_fetcher.stock_list.return_value = pd.DataFrame({
            "code": ["000001", "600519"],
            "name": ["平安银行", "贵州茅台"],
        })

        with patch("zhanfa.api.services.watchlist_service.Fetcher", return_value=mock_fetcher):
            result = batch_add_items(db_session, wl["id"], ["1", "600519"])

        codes = [item["code"] for item in result["items"]]
        assert codes == ["000001", "600519"]
        assert db_session.get(Stock, "000001") is not None
        assert db_session.get(Stock, "600519") is not None


class TestBatchMoveItems:
    def test_moves_between_lists(self, db_with_stock):
        wl1 = create_watchlist(db_with_stock, "Source")
        wl2 = create_watchlist(db_with_stock, "Target")
        add_item(db_with_stock, wl1["id"], "000001")
        result = batch_move_items(db_with_stock, wl1["id"], wl2["id"], ["000001"])
        assert len(result["items"]) == 0  # source is now empty

    def test_returns_none_for_missing_wl(self, db_session):
        assert batch_move_items(db_session, 99999, 99998, ["000001"]) is None


class TestSearchStocks:
    def test_searches_by_code(self, db_with_stock):
        from zhanfa.api.services.watchlist_service import search_stocks
        results = search_stocks(db_with_stock, "000001")
        assert len(results) >= 1
        assert results[0]["code"] == "000001"

    def test_searches_by_name(self, db_with_stock):
        from zhanfa.api.services.watchlist_service import search_stocks
        results = search_stocks(db_with_stock, "茅台")
        assert any(r["code"] == "600519" for r in results)

    def test_empty_query_returns_empty(self, db_session):
        from zhanfa.api.services.watchlist_service import search_stocks
        assert search_stocks(db_session, "") == []


class TestExportCsv:
    def test_exports_csv(self, db_with_stock):
        wl = create_watchlist(db_with_stock, "Test")
        add_item(db_with_stock, wl["id"], "000001")
        csv_str = export_csv(db_with_stock, wl["id"])
        assert csv_str is not None
        assert "code" in csv_str
        assert "000001" in csv_str

    def test_returns_none_for_missing(self, db_session):
        assert export_csv(db_session, 99999) is None


class TestGetWatchlistQuotes:
    def test_returns_quotes(self, db_with_stock):
        from zhanfa.api.services.watchlist_service import get_watchlist_quotes

        wl = create_watchlist(db_with_stock, "Test")
        add_item(db_with_stock, wl["id"], "000001")

        mock_df = pd.DataFrame({
            "open": [10.0, 11.0], "high": [12.0, 13.0],
            "low": [9.0, 10.0], "close": [11.0, 12.0],
            "volume": [1000, 2000],
        })
        mock_fin = pd.DataFrame({"pe": [15.0], "pb": [2.0], "dividend_yield": [0.02]})

        mock_fetcher = MagicMock()
        mock_fetcher.daily.return_value = mock_df

        mock_store = MagicMock()
        mock_store.last_closes.return_value = {"000001": None}  # force fallback to Fetcher
        mock_store.date_ranges.return_value = {"000001": None}
        mock_store.load.return_value = mock_fin

        with (
            patch("zhanfa.api.services.watchlist_service.Fetcher", return_value=mock_fetcher),
            patch("zhanfa.data.store.Store", return_value=mock_store),
        ):
            result = get_watchlist_quotes(db_with_stock, wl["id"])
            assert result is not None
            assert result["id"] == wl["id"]
            assert len(result["items"]) == 1
            item = result["items"][0]
            assert item["code"] == "000001"
            assert item["latest_price"] == 12.0
            assert item["pe"] == 15.0
            assert item["pb"] == 2.0
            assert item["data_status"]["has_daily"] is True  # Fetcher fallback sets it
            assert item["data_freshness"] == "live"

    def test_returns_quotes_from_cache(self, db_with_stock):
        """When cache is available, use it for price and mark freshness."""
        from zhanfa.api.services.watchlist_service import get_watchlist_quotes

        wl = create_watchlist(db_with_stock, "Test")
        add_item(db_with_stock, wl["id"], "600519")

        mock_fin = pd.DataFrame({"pe": [20.0], "pb": [3.0], "dividend_yield": [0.015]})

        mock_fetcher = MagicMock()

        from datetime import datetime, timedelta, timezone

        mock_store = MagicMock()
        mock_store.last_closes.return_value = {"600519": {"close": 1685.5, "prev_close": 1650.0}}
        mock_store.date_ranges.return_value = {"600519": {"start": None, "end": None, "rows": 100}}
        mock_store.mtime.return_value = datetime.now(timezone.utc) - timedelta(hours=2)
        mock_store.load.return_value = mock_fin

        with (
            patch("zhanfa.api.services.watchlist_service.Fetcher", return_value=mock_fetcher),
            patch("zhanfa.data.store.Store", return_value=mock_store),
        ):
            result = get_watchlist_quotes(db_with_stock, wl["id"])
            assert result is not None
            item = result["items"][0]
            assert item["latest_price"] == 1685.5
            assert item["change_pct"] == pytest.approx((1685.5 - 1650.0) / 1650.0)
            assert item["data_status"]["has_daily"] is True
            assert item["data_freshness"] == "cached_2h"

    def test_returns_none_for_missing_wl(self, db_session):
        from zhanfa.api.services.watchlist_service import get_watchlist_quotes
        assert get_watchlist_quotes(db_session, 99999) is None

    def test_empty_watchlist_returns_empty_items(self, db_session):
        """get_watchlist_quotes for an empty watchlist returns items=[]."""
        from zhanfa.api.services.watchlist_service import get_watchlist_quotes
        wl = create_watchlist(db_session, "Empty")
        result = get_watchlist_quotes(db_session, wl["id"])
        assert result is not None
        assert result["items"] == []

    def test_change_pct_none_when_no_prev_close(self, db_with_stock):
        """change_pct is None when prev_close is unavailable."""
        from zhanfa.api.services.watchlist_service import get_watchlist_quotes

        from datetime import datetime, timedelta, timezone

        wl = create_watchlist(db_with_stock, "Test")
        add_item(db_with_stock, wl["id"], "000001")

        mock_fin = pd.DataFrame({"pe": [15.0], "pb": [2.0], "dividend_yield": [0.02]})
        mock_fetcher = MagicMock()

        mock_store = MagicMock()
        mock_store.last_closes.return_value = {"000001": {"close": 10.0}}  # no prev_close
        mock_store.date_ranges.return_value = {"000001": {"start": None, "end": None, "rows": 100}}
        mock_store.mtime.return_value = datetime.now(timezone.utc) - timedelta(hours=2)
        mock_store.load.return_value = mock_fin

        with (
            patch("zhanfa.api.services.watchlist_service.Fetcher", return_value=mock_fetcher),
            patch("zhanfa.data.store.Store", return_value=mock_store),
        ):
            result = get_watchlist_quotes(db_with_stock, wl["id"])
            item = result["items"][0]
            assert item["latest_price"] == 10.0
            assert item["change_pct"] is None

    def test_financial_missing_yields_none_values(self, db_with_stock):
        """When financial data is unavailable, pe/pb/dividend_yield are None."""
        from zhanfa.api.services.watchlist_service import get_watchlist_quotes

        wl = create_watchlist(db_with_stock, "Test")
        add_item(db_with_stock, wl["id"], "000001")

        mock_fetcher = MagicMock()

        from datetime import datetime, timedelta, timezone

        mock_store = MagicMock()
        mock_store.last_closes.return_value = {"000001": {"close": 10.0, "prev_close": 9.5}}
        mock_store.date_ranges.return_value = {"000001": None}  # no financial cache
        mock_store.mtime.return_value = datetime.now(timezone.utc) - timedelta(hours=1)
        mock_store.load.side_effect = RuntimeError("unavailable")  # financial read fails

        with (
            patch("zhanfa.api.services.watchlist_service.Fetcher", return_value=mock_fetcher),
            patch("zhanfa.data.store.Store", return_value=mock_store),
        ):
            result = get_watchlist_quotes(db_with_stock, wl["id"])
            item = result["items"][0]
            assert item["pe"] is None
            assert item["pb"] is None
            assert item["dividend_yield"] is None

    def test_data_freshness_unknown_when_no_cache_or_fetch(self, db_with_stock):
        """data_freshness is 'unknown' when both cache and fetcher fail."""
        from zhanfa.api.services.watchlist_service import get_watchlist_quotes

        wl = create_watchlist(db_with_stock, "Test")
        add_item(db_with_stock, wl["id"], "000001")

        mock_fetcher = MagicMock()
        mock_fetcher.daily.side_effect = RuntimeError("offline")

        mock_store = MagicMock()
        mock_store.last_closes.return_value = {"000001": None}
        mock_store.date_ranges.return_value = {"000001": None}
        mock_store.load.side_effect = RuntimeError("offline")

        with (
            patch("zhanfa.api.services.watchlist_service.Fetcher", return_value=mock_fetcher),
            patch("zhanfa.data.store.Store", return_value=mock_store),
        ):
            result = get_watchlist_quotes(db_with_stock, wl["id"])
            item = result["items"][0]
            assert item["latest_price"] is None
            assert item["data_freshness"] == "unknown"
            assert item["data_status"]["has_daily"] is False

    def test_partial_failure_logs_code_and_preserves_other_stocks(self, db_with_stock, caplog):
        """When one stock's daily fetch fails, others still get data; log includes code."""
        import logging
        from zhanfa.api.services.watchlist_service import get_watchlist_quotes

        wl = create_watchlist(db_with_stock, "Test")
        add_item(db_with_stock, wl["id"], "000001")
        add_item(db_with_stock, wl["id"], "600519")

        def daily_side_effect(code):
            if code == "000001":
                raise RuntimeError("network error")
            return pd.DataFrame({
                "open": [10.0], "high": [11.0], "low": [9.0], "close": [10.5], "volume": [1000],
            })

        mock_fin = pd.DataFrame({"pe": [15.0], "pb": [2.0], "dividend_yield": [0.02]})

        mock_fetcher = MagicMock()
        mock_fetcher.daily.side_effect = daily_side_effect

        mock_store = MagicMock()
        mock_store.last_closes.return_value = {"000001": None, "600519": None}  # force Fetcher fallback
        mock_store.date_ranges.return_value = {"000001": None, "600519": None}
        mock_store.load.return_value = mock_fin

        with (
            patch("zhanfa.api.services.watchlist_service.Fetcher", return_value=mock_fetcher),
            patch("zhanfa.data.store.Store", return_value=mock_store),
        ):
            with caplog.at_level(logging.WARNING):
                result = get_watchlist_quotes(db_with_stock, wl["id"])

        assert result is not None
        assert len(result["items"]) == 2

        # Stock 000001 failed — should have no price data
        item_failed = [i for i in result["items"] if i["code"] == "000001"][0]
        assert item_failed["latest_price"] is None
        assert item_failed["data_freshness"] == "unknown"

        # Stock 600519 succeeded — should have price data
        item_ok = [i for i in result["items"] if i["code"] == "600519"][0]
        assert item_ok["latest_price"] == 10.5
        assert item_ok["data_freshness"] == "live"

        # Log should contain the failing code
        warnings = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
        assert any("000001" in msg for msg in warnings), (
            f"Expected warning with failing code=000001, got: {warnings}"
        )


class TestGetWatchlistQuotesPerformance:
    """TICKET-048: Performance regression tests for batch cache reads."""

    def test_cache_hit_avoids_live_fetch(self, db_with_stock):
        """N cached stocks should NOT trigger N live fetches."""
        from zhanfa.api.services.watchlist_service import get_watchlist_quotes

        wl = create_watchlist(db_with_stock, "Perf")
        batch_add_items(db_with_stock, wl["id"], ["000001", "600519"])

        mock_fin = pd.DataFrame({"pe": [15.0], "pb": [2.0], "dividend_yield": [0.02]})
        mock_fetcher = MagicMock()
        mock_fetcher.financial.return_value = mock_fin

        from datetime import datetime, timedelta, timezone

        mock_store = MagicMock()
        mock_store.last_closes.return_value = {
            "000001": {"close": 10.0, "prev_close": 9.5},
            "600519": {"close": 1685.5, "prev_close": 1650.0},
        }
        mock_store.date_ranges.return_value = {
            "000001": {"start": None, "end": None, "rows": 100},
            "600519": {"start": None, "end": None, "rows": 200},
        }
        mock_store.mtime.return_value = datetime.now(timezone.utc) - timedelta(hours=2)
        # Store.load returns cached financial
        mock_store.load.return_value = mock_fin

        with (
            patch("zhanfa.api.services.watchlist_service.Fetcher", return_value=mock_fetcher),
            patch("zhanfa.data.store.Store", return_value=mock_store),
        ):
            result = get_watchlist_quotes(db_with_stock, wl["id"])

        assert result is not None
        assert len(result["items"]) == 2
        # Cache hit: Fetcher.daily should never be called
        mock_fetcher.daily.assert_not_called()

    def test_only_cache_miss_triggers_live_fetch(self, db_with_stock):
        """Only stocks with cache miss fall back to live fetch."""
        from zhanfa.api.services.watchlist_service import get_watchlist_quotes

        wl = create_watchlist(db_with_stock, "Perf")
        batch_add_items(db_with_stock, wl["id"], ["000001", "600519"])

        mock_fin = pd.DataFrame({"pe": [15.0], "pb": [2.0], "dividend_yield": [0.02]})

        mock_fetcher = MagicMock()
        mock_fetcher.daily.return_value = pd.DataFrame({
            "open": [10.0], "high": [11.0], "low": [9.0], "close": [10.5], "volume": [1000],
        })
        mock_fetcher.financial.return_value = mock_fin

        from datetime import datetime, timedelta, timezone

        mock_store = MagicMock()
        # 000001 is cached, 600519 is miss
        mock_store.last_closes.return_value = {
            "000001": {"close": 10.0, "prev_close": 9.5},
            "600519": None,
        }
        mock_store.date_ranges.return_value = {
            "000001": {"start": None, "end": None, "rows": 100},
            "600519": None,
        }
        mock_store.mtime.return_value = datetime.now(timezone.utc) - timedelta(hours=2)
        mock_store.load.return_value = mock_fin

        with (
            patch("zhanfa.api.services.watchlist_service.Fetcher", return_value=mock_fetcher),
            patch("zhanfa.data.store.Store", return_value=mock_store),
        ):
            result = get_watchlist_quotes(db_with_stock, wl["id"])

        assert result is not None
        # Only 600519 triggered fetch
        mock_fetcher.daily.assert_called_once_with("600519")


class TestAddItemEdgeCases:
    def test_add_with_notes_on_first_add(self, db_with_stock):
        """Adding a new item with notes preserves both code and notes."""
        wl = create_watchlist(db_with_stock, "Test")
        result = add_item(db_with_stock, wl["id"], "000001", notes="initial note")
        item = [i for i in result["items"] if i["code"] == "000001"][0]
        assert item["notes"] == "initial note"

    def test_re_add_after_remove(self, db_with_stock):
        """Removing an item then re-adding it works correctly."""
        wl = create_watchlist(db_with_stock, "Test")
        add_item(db_with_stock, wl["id"], "000001")
        remove_item(db_with_stock, wl["id"], "000001")
        result = add_item(db_with_stock, wl["id"], "000001", notes="重回关注")
        assert result["stock_count"] == 1
        assert result["items"][0]["notes"] == "重回关注"

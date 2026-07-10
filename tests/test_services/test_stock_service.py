"""Stock service tests."""

from __future__ import annotations

import pandas as pd

from zhanfa.api.services import stock_service


def _daily_df() -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=30, freq="B")
    return pd.DataFrame(
        {
            "open": [10.0] * len(dates),
            "high": [11.0] * len(dates),
            "low": [9.0] * len(dates),
            "close": [10.0 + i * 0.1 for i in range(len(dates))],
            "volume": [1000] * len(dates),
        },
        index=dates,
    )


def _financial_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "net_profit": [10.0, 12.0],
            "revenue": [100.0, 120.0],
            "eps": [0.5, 0.6],
            "roe": [0.1, 0.12],
            "debt_ratio": [0.3, 0.28],
            "gross_margin": [0.4, 0.42],
        },
        index=pd.to_datetime(["2023-12-31", "2024-12-31"]),
    )


class FakeFetcher:
    def __init__(self, financial: pd.DataFrame | None = None):
        self._financial = financial if financial is not None else _financial_df()

    def stock_list(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {"code": "000001", "name": "平安银行"},
                {"code": "600519", "name": "贵州茅台"},
            ]
        )

    def daily(self, code: str, start: str = "20100101", end: str = "21000101") -> pd.DataFrame:
        return _daily_df()

    def financial(self, code: str) -> pd.DataFrame:
        return self._financial

    def industry_stocks(self, industry: str) -> pd.DataFrame:
        return pd.DataFrame([{"code": "000001", "name": "平安银行"}])


def test_list_stocks_paginates(monkeypatch):
    monkeypatch.setattr(stock_service, "Fetcher", FakeFetcher)

    result = stock_service.list_stocks(page=2, page_size=1)

    assert result["total"] == 2
    assert result["items"] == [{"code": "600519", "name": "贵州茅台"}]


def test_get_stock_meta_includes_latest_financial(monkeypatch):
    monkeypatch.setattr(stock_service, "Fetcher", FakeFetcher)

    result = stock_service.get_stock_meta("000001")

    assert result is not None
    assert result["code"] == "000001"
    assert result["latest_financial"]["report_date"] == "2024-12-31"
    assert result["latest_financial"]["roe"] == 0.12


def test_get_stock_meta_returns_none_for_missing(monkeypatch):
    monkeypatch.setattr(stock_service, "Fetcher", FakeFetcher)

    assert stock_service.get_stock_meta("999999") is None


def test_get_stock_meta_degrades_when_db_unavailable(monkeypatch):
    monkeypatch.setattr(stock_service, "Fetcher", FakeFetcher)

    def raise_db_unavailable():
        raise RuntimeError("db down")

    monkeypatch.setattr("zhanfa.db.base.SessionLocal", raise_db_unavailable)

    result = stock_service.get_stock_meta("000001")

    assert result is not None
    assert result["name"] == "平安银行"
    assert result["latest_financial"] is not None


def test_get_daily_serializes_ohlcv(monkeypatch):
    monkeypatch.setattr(stock_service, "Fetcher", FakeFetcher)

    result = stock_service.get_daily("000001")

    assert result["code"] == "000001"
    assert result["count"] == 30
    assert result["data"][0]["open"] == 10.0


def test_get_financial_empty_returns_shape(monkeypatch):
    monkeypatch.setattr(stock_service, "Fetcher", lambda: FakeFetcher(pd.DataFrame()))

    result = stock_service.get_financial("000001", years=3)

    assert result == {"code": "000001", "years": 3, "data": []}


def test_get_indicators_returns_tail_shape(monkeypatch):
    monkeypatch.setattr(stock_service, "Fetcher", FakeFetcher)

    result = stock_service.get_indicators("000001")

    assert result["code"] == "000001"
    assert result["count"] == 30
    assert {"sma_20", "macd_dif", "rsi_14", "boll_upper"}.issubset(result["data"][-1])


def test_get_industry_comparison_uses_cached_financial(monkeypatch):
    class FakeStore:
        def load(self, code: str, freq: str):
            assert (code, freq) == ("000001", "financial")
            return _financial_df()

    monkeypatch.setattr(stock_service, "Fetcher", FakeFetcher)
    monkeypatch.setattr("zhanfa.data.store.Store", lambda: FakeStore())

    result = stock_service.get_industry_comparison("银行")

    assert result["industry"] == "银行"
    assert result["peers"][0]["roe"] == 0.12
    assert result["peers"][0]["data_freshness"] == "cached"

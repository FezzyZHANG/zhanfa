"""Data import service tests."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from zhanfa.db.import_data import _to_date, _extract_financial_fields, _update_financial
from zhanfa.db.models import Stock, StockFinancial


class TestToDate:
    def test_date_returns_itself(self):
        from datetime import date
        d = date(2024, 1, 15)
        assert _to_date(d) == d

    def test_datetime_returns_date(self):
        from datetime import datetime
        d = datetime(2024, 1, 15, 12, 30)
        result = _to_date(d)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_timestamp_returns_date(self):
        ts = pd.Timestamp("2024-01-15")
        result = _to_date(ts)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_none_returns_none(self):
        assert _to_date(None) is None

    def test_string_returns_none(self):
        assert _to_date("2024-01-15") is None


class TestExtractFinancialFields:
    def test_extracts_known_fields(self):
        row = pd.Series({
            "net_profit": 10.5, "revenue": 100.0, "eps": 0.5,
            "roe": 15.0, "debt_ratio": 40.0, "current_ratio": 1.5,
            "net_margin": 12.0,
        })
        result = _extract_financial_fields(row)
        assert result["net_profit"] == 10.5
        assert result["eps"] == 0.5
        assert result["roe"] == 15.0

    def test_skips_nan_values(self):
        row = pd.Series({"net_profit": float("nan"), "revenue": 100.0})
        result = _extract_financial_fields(row)
        assert "net_profit" not in result
        assert result["revenue"] == 100.0

    def test_skips_missing_columns(self):
        row = pd.Series({"eps": 0.5})
        result = _extract_financial_fields(row)
        assert result == {"eps": 0.5}


class TestUpdateFinancial:
    def test_sets_attributes(self):
        existing = MagicMock(spec=StockFinancial)
        row = pd.Series({"net_profit": 10.5, "eps": 0.5})
        _update_financial(existing, row)
        assert existing.net_profit == 10.5
        assert existing.eps == 0.5


class TestImportStocks:
    def test_returns_zero_when_no_file(self, db_session):
        from zhanfa.db.import_data import import_stocks
        from zhanfa.db.base import SessionLocal

        mock_store = MagicMock()
        mock_store.load.return_value = None

        with patch("zhanfa.db.import_data.SessionLocal", return_value=db_session):
            result = import_stocks(store=mock_store)
            assert result == 0

    def test_imports_stocks_from_df(self, db_session):
        from zhanfa.db.import_data import import_stocks
        from zhanfa.db.base import SessionLocal

        df = pd.DataFrame({
            "code": ["000001", "600519", "301234"],
            "name": ["平安银行", "贵州茅台", "测试"],
        })
        mock_store = MagicMock()
        mock_store.load.return_value = df

        with patch("zhanfa.db.import_data.SessionLocal", return_value=db_session):
            result = import_stocks(store=mock_store)
            assert result == 3

        assert db_session.get(Stock, "000001").name == "平安银行"
        assert db_session.get(Stock, "000001").exchange == "SZ"
        assert db_session.get(Stock, "600519").exchange == "SH"


class TestImportFinancials:
    def test_returns_zero_when_no_codes(self, db_session):
        from zhanfa.db.import_data import import_financials
        from zhanfa.db.base import SessionLocal

        mock_store = MagicMock()
        mock_store.codes.return_value = []

        with patch("zhanfa.db.import_data.SessionLocal", return_value=db_session):
            result = import_financials(store=mock_store)
            assert result == 0


class TestImportAll:
    def test_returns_dict(self):
        from zhanfa.db.import_data import import_all
        from zhanfa.db.base import SessionLocal

        mock_store = MagicMock()
        mock_store.load.return_value = None
        mock_store.codes.return_value = []

        with (
            patch("zhanfa.db.import_data.Store") as mock_store_cls,
            patch("zhanfa.db.import_data.SessionLocal") as mock_session,
        ):
            mock_store_cls.return_value = mock_store
            mock_session.return_value = MagicMock()
            result = import_all()
            assert "stocks" in result
            assert "financials" in result

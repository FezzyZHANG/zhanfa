"""Stock metadata import tests."""

import pandas as pd
import pytest

from zhanfa.db.import_data import import_stocks_from_frame, normalize_stock_code
from zhanfa.db.models import Stock


def test_normalize_stock_code():
    assert normalize_stock_code("1") == "000001"
    assert normalize_stock_code(1) == "000001"
    assert normalize_stock_code("600519") == "600519"


def test_normalize_stock_code_rejects_non_digit():
    with pytest.raises(ValueError, match="Invalid stock code"):
        normalize_stock_code("../000001")


def test_import_stocks_from_frame_is_idempotent(db_session):
    df = pd.DataFrame({
        "code": ["1", "600519"],
        "name": ["平安银行", "贵州茅台"],
        "industry": ["银行", "白酒"],
    })

    assert import_stocks_from_frame(df, session=db_session) == 2
    assert import_stocks_from_frame(df, session=db_session) == 2

    stocks = db_session.query(Stock).order_by(Stock.code).all()
    assert [stock.code for stock in stocks] == ["000001", "600519"]
    assert stocks[0].name == "平安银行"
    assert stocks[0].industry == "银行"

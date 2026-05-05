"""从 parquet 数据导入股票元信息和财报到数据库"""

from datetime import date, datetime
from pathlib import Path

import pandas as pd

from zhanfa.data.store import Store
from zhanfa.db.base import SessionLocal
from zhanfa.db.models import Stock, StockFinancial


def normalize_stock_code(code) -> str:
    """Normalize A-share codes to six digits when possible."""
    text = str(code).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text.zfill(6) if text.isdigit() else text


def import_stocks_from_frame(df: pd.DataFrame, session=None) -> int:
    """Import stock metadata from an in-memory DataFrame.

    Expected columns are `code` and `name`; optional `industry` is used when present.
    """
    owns_session = session is None
    session = session or SessionLocal()
    count = 0
    try:
        for _, row in df.iterrows():
            code = normalize_stock_code(row["code"])
            name = str(row["name"])
            existing = session.get(Stock, code)
            if existing:
                existing.name = name
                if "industry" in row.index and pd.notna(row["industry"]):
                    existing.industry = str(row["industry"])
                existing.updated_at = datetime.now()
            else:
                session.add(Stock(
                    code=code,
                    name=name,
                    exchange=_infer_exchange(code),
                    industry=str(row["industry"]) if "industry" in row.index and pd.notna(row["industry"]) else None,
                ))
            count += 1
        if owns_session:
            session.commit()
        else:
            session.flush()
    except Exception:
        if owns_session:
            session.rollback()
        raise
    finally:
        if owns_session:
            session.close()
    return count


def import_stocks(store: Store | None = None, data_dir: str = "data") -> int:
    """从 meta/stock_list.parquet 导入股票元信息。

    Returns:
        导入的股票数量。
    """
    if store is None:
        store = Store(data_dir)

    df = store.load("stock_list", "meta")
    if df is None:
        print("stock_list.parquet not found, skipping stock import")
        return 0

    return import_stocks_from_frame(df)


def import_financials(store: Store | None = None, data_dir: str = "data") -> int:
    """从 financial/*.parquet 导入财报数据。

    Returns:
        导入的财报记录数。
    """
    if store is None:
        store = Store(data_dir)

    codes = store.codes("financial")
    if not codes:
        codes = []
        fin_dir = Path(data_dir) / "financial"
        if fin_dir.exists():
            codes = [f.stem for f in fin_dir.glob("*.parquet")]

    if not codes:
        print("No financial parquet files found, skipping financial import")
        return 0

    session = SessionLocal()
    count = 0
    try:
        for code in codes:
            df = store.load(code, "financial")
            if df is None:
                continue
            for idx, row in df.iterrows():
                rpt_date = _to_date(idx)
                if rpt_date is None:
                    continue
                existing = session.query(StockFinancial).filter_by(
                    code=code, report_date=rpt_date
                ).first()
                if existing:
                    _update_financial(existing, row)
                else:
                    session.add(StockFinancial(
                        code=code,
                        report_date=rpt_date,
                        **_extract_financial_fields(row),
                    ))
                count += 1
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    return count


def import_all(data_dir: str = "data") -> dict[str, int]:
    """一键导入股票和财报数据。

    Returns:
        {"stocks": n, "financials": n}
    """
    store = Store(data_dir)
    n_stocks = import_stocks(store, data_dir)
    n_fin = import_financials(store, data_dir)
    print(f"Imported {n_stocks} stocks, {n_fin} financial records")
    return {"stocks": n_stocks, "financials": n_fin}


def _to_date(val) -> date | None:
    """将各种格式的日期转为 date 对象"""
    if isinstance(val, date):
        return val
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, pd.Timestamp):
        return val.date()
    return None


def _extract_financial_fields(row: pd.Series) -> dict:
    """从 DataFrame 行提取财报字段"""
    field_map = {
        "net_profit": "net_profit",
        "revenue": "revenue",
        "eps": "eps",
        "roe": "roe",
        "debt_ratio": "debt_ratio",
        "current_ratio": "current_ratio",
        "net_margin": "net_margin",
        "gross_margin": "gross_margin",
        "dividend_yield": "dividend_yield",
        "pe": "pe",
        "pb": "pb",
    }
    result = {}
    for src, dst in field_map.items():
        if src in row.index:
            val = row[src]
            if pd.notna(val):
                result[dst] = float(val)
    return result


def _update_financial(existing: StockFinancial, row: pd.Series) -> None:
    """更新已有财报记录的字段"""
    fields = _extract_financial_fields(row)
    for k, v in fields.items():
        setattr(existing, k, v)


def _infer_exchange(code: str) -> str:
    if code.startswith(("0", "3")):
        return "SZ"
    if code.startswith("6"):
        return "SH"
    if code.startswith(("4", "8")):
        return "BJ"
    return ""

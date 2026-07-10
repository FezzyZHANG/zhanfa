"""Stock data service — wraps Fetcher, Store, Pipeline for API use."""

from __future__ import annotations

import logging

import pandas as pd

from zhanfa.data import Fetcher
from zhanfa.data.pipeline import Pipeline
from zhanfa.strategies import indicators as ind

logger = logging.getLogger(__name__)


def list_stocks(page: int = 1, page_size: int = 50) -> dict:
    fetcher = Fetcher()
    df = fetcher.stock_list()
    total = len(df)
    start = (page - 1) * page_size
    end = start + page_size
    items = []
    for _, row in df.iloc[start:end].iterrows():
        items.append({"code": str(row["code"]), "name": str(row["name"])})
    return {"total": total, "page": page, "page_size": page_size, "items": items}


def get_stock_meta(code: str) -> dict | None:
    fetcher = Fetcher()
    stocks = fetcher.stock_list()
    match = stocks[stocks["code"].astype(str) == str(code)]
    if match.empty:
        return None
    row = match.iloc[0]
    result: dict[str, object] = {
        "code": str(row["code"]),
        "name": str(row["name"]),
        "exchange": None,
        "industry": None,
        "market_cap": None,
        "listed_date": None,
    }

    # Try DB for extended fields
    try:
        from zhanfa.db.base import SessionLocal
        from zhanfa.db.models import Stock as StockModel

        with SessionLocal() as s:
            db_stock = s.query(StockModel).filter(StockModel.code == str(code)).first()
            if db_stock:
                result["exchange"] = db_stock.exchange
                result["industry"] = db_stock.industry
                result["market_cap"] = db_stock.market_cap
                if db_stock.listed_date:
                    result["listed_date"] = db_stock.listed_date.isoformat()
    except Exception:
        logger.warning("Failed to query stock metadata from DB (code=%s)", code, exc_info=True)

    try:
        fin = fetcher.financial(code)
        if not fin.empty:
            latest = fin.iloc[-1]
            result["latest_financial"] = _serialize_financial_row(latest)
    except Exception:
        logger.warning("Failed to query latest financial data (code=%s)", code, exc_info=True)
        result["latest_financial"] = None

    return result


def get_daily(
    code: str, start: str = "20100101", end: str = "21000101", freq: str = "daily"
) -> dict:
    fetcher = Fetcher()
    if freq in ("60min", "30min", "15min", "1h"):
        period = "60" if freq == "1h" else freq.replace("min", "")
        df = fetcher.minute(code, period=period)
    else:
        df = fetcher.daily(code, start=start, end=end)
    df = Pipeline.clean(df)
    return _serialize_ohlcv(code, df)


def get_financial(code: str, years: int = 3) -> dict:
    fetcher = Fetcher()
    df = fetcher.financial(code)
    if df.empty:
        return {"code": code, "years": years, "data": []}

    cutoff = pd.Timestamp.now() - pd.DateOffset(years=years)
    df = df[df.index >= cutoff]

    data = [_serialize_financial_row(row) for _, row in df.iterrows()]
    return {"code": code, "years": years, "data": data}


def get_indicators(code: str, start: str = "20100101", end: str = "21000101") -> dict:
    fetcher = Fetcher()
    df = fetcher.daily(code, start=start, end=end)
    df = Pipeline.clean(df)
    df = Pipeline.add_simple_indicators(df)

    close = df["close"]
    macd_df = ind.macd(close)
    rsi_series = ind.rsi(close)
    boll_df = ind.bollinger(close)

    tail = df.iloc[-252:]  # last ~1 year
    data = []
    for idx, row in tail.iterrows():
        date_val = idx.to_pydatetime() if hasattr(idx, "to_pydatetime") else idx
        data.append(
            {
                "date": date_val,
                "sma_20": _nan_to_none(row.get("sma_20")),
                "sma_60": _nan_to_none(row.get("sma_60")),
                "sma_120": _nan_to_none(row.get("sma_120")),
                "macd_dif": _nan_to_none(macd_df.loc[idx, "dif"])  # type: ignore[index]
                if idx in macd_df.index
                else None,
                "macd_dea": _nan_to_none(macd_df.loc[idx, "dea"])  # type: ignore[index]
                if idx in macd_df.index
                else None,
                "macd_bar": _nan_to_none(macd_df.loc[idx, "bar"])  # type: ignore[index]
                if idx in macd_df.index
                else None,
                "rsi_14": _nan_to_none(rsi_series.loc[idx])  # type: ignore[call-overload]
                if idx in rsi_series.index
                else None,
                "boll_upper": _nan_to_none(boll_df.loc[idx, "upper"])  # type: ignore[index]
                if idx in boll_df.index
                else None,
                "boll_mid": _nan_to_none(boll_df.loc[idx, "mid"])  # type: ignore[index]
                if idx in boll_df.index
                else None,
                "boll_lower": _nan_to_none(boll_df.loc[idx, "lower"])  # type: ignore[index]
                if idx in boll_df.index
                else None,
            }
        )

    return {"code": code, "count": len(data), "data": data}


def get_industry_comparison(industry: str, limit: int = 20) -> dict:
    fetcher = Fetcher()
    stocks = fetcher.industry_stocks(industry)
    if stocks.empty:
        return {"industry": industry, "peers": []}

    from zhanfa.data.store import Store
    store = Store()

    # Cap the number of peers to compare
    stocks = stocks.head(limit)

    peers = []
    for _, row in stocks.iterrows():
        code = str(row["code"])
        name = str(row.get("name", ""))
        peer: dict[str, object] = {
            "code": code,
            "name": name,
            "roe": None,
            "gross_margin": None,
            "debt_ratio": None,
            "revenue_growth": None,
            "net_profit_growth": None,
            "data_freshness": "missing",
        }
        try:
            # Cache-first: try Store.load before live fetch
            fin = store.load(code, "financial")
            from_cache = fin is not None
            if not from_cache:
                fin = fetcher.financial(code)

            if fin is not None and not fin.empty and len(fin) >= 2:
                latest = fin.iloc[-1]
                prev = fin.iloc[-2]
                peer["roe"] = _safe_float_none(latest.get("roe"))
                peer["gross_margin"] = _safe_float_none(latest.get("gross_margin"))
                peer["debt_ratio"] = _safe_float_none(latest.get("debt_ratio"))
                rev_latest = _safe_float_none(latest.get("revenue"))
                rev_prev = _safe_float_none(prev.get("revenue"))
                np_latest = _safe_float_none(latest.get("net_profit"))
                np_prev = _safe_float_none(prev.get("net_profit"))
                if rev_latest and rev_prev and rev_prev != 0:
                    peer["revenue_growth"] = (rev_latest - rev_prev) / abs(rev_prev)
                if np_latest and np_prev and np_prev != 0:
                    peer["net_profit_growth"] = (np_latest - np_prev) / abs(np_prev)
                peer["data_freshness"] = "cached" if from_cache else "live"
            elif fin is not None and not fin.empty:
                # Only 1 period available — fill static indicators, no growth
                latest = fin.iloc[-1]
                peer["roe"] = _safe_float_none(latest.get("roe"))
                peer["gross_margin"] = _safe_float_none(latest.get("gross_margin"))
                peer["debt_ratio"] = _safe_float_none(latest.get("debt_ratio"))
                peer["data_freshness"] = "cached" if from_cache else "live"
        except Exception:
            logger.warning(
                "Failed to build industry comparison peer (industry=%s, code=%s)",
                industry,
                code,
                exc_info=True,
            )
        peers.append(peer)

    return {"industry": industry, "peers": peers}


def _safe_float_none(val) -> float | None:
    """Like _safe_float but returns None on missing, to distinguish 0 from missing."""
    if val is None:
        return None
    try:
        v = float(val)
        return v if v == v else None
    except (ValueError, TypeError):
        return None


def _safe_float(val) -> float:
    if val is None:
        return 0
    try:
        v = float(val)
        return v if v == v else 0
    except (ValueError, TypeError):
        return 0


def _nan_to_none(val):
    if isinstance(val, float) and pd.isna(val):
        return None
    return val


def _serialize_ohlcv(code: str, df: pd.DataFrame) -> dict:
    data = []
    for idx, row in df.iterrows():
        date_val = idx.to_pydatetime() if hasattr(idx, "to_pydatetime") else idx
        data.append(
            {
                "date": date_val,
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"]),
                "amount": float(row.get("amount"))  # type: ignore[arg-type]
                if "amount" in row and not pd.isna(row["amount"])
                else None,
            }
        )
    return {"code": code, "count": len(data), "data": data}


def _serialize_financial_row(row) -> dict:
    idx = row.name if hasattr(row, "name") else None
    report_date: str
    if hasattr(idx, "date"):
        report_date = idx.date().isoformat()  # type: ignore[union-attr]
    elif idx is not None:
        report_date = str(idx)
    else:
        report_date = ""
    return {
        "report_date": report_date,
        "net_profit": _nan_to_none(row.get("net_profit")),
        "revenue": _nan_to_none(row.get("revenue")),
        "eps": _nan_to_none(row.get("eps")),
        "roe": _nan_to_none(row.get("roe")),
        "debt_ratio": _nan_to_none(row.get("debt_ratio")),
        "net_margin": _nan_to_none(row.get("net_margin")),
    }

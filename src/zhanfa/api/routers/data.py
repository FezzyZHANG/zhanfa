"""Data management router — stats, stock status, and refresh."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query

from zhanfa.api.models import (
    CacheStats,
    DataStats,
    DBStats,
    InitializeResult,
    RefreshRequest,
    RefreshResult,
    RefreshError,
    StockDataStatus,
)
from zhanfa.automation.workflows import update_daily_data, update_minute_data
from zhanfa.data.fetcher import Fetcher
from zhanfa.data.store import Store
from zhanfa.db.base import SessionLocal
from zhanfa.db.import_data import import_stocks
from zhanfa.db.models import BacktestResult, Stock, StockFinancial, Strategy, Watchlist

router = APIRouter(prefix="/api/data", tags=["data"])


# ── Helpers ─────────────────────────────────────────

def _db_stats() -> DBStats:
    with SessionLocal() as s:
        return DBStats(
            stock_count=s.query(Stock).count(),
            financial_count=s.query(StockFinancial).count(),
            watchlist_count=s.query(Watchlist).count(),
            strategy_count=s.query(Strategy).count(),
            backtest_count=s.query(BacktestResult).count(),
        )


def _stock_name(code: str, store: Store) -> str:
    """Try cache first, then DB, for a human-readable stock name."""
    try:
        sl = store.load("stock_list", "meta")
        if sl is not None:
            match = sl[sl["code"].astype(str) == str(code)]
            if not match.empty:
                return str(match.iloc[0]["name"])
    except Exception:
        pass
    with SessionLocal() as s:
        st = s.query(Stock).filter(Stock.code == code).first()
        if st:
            return st.name
    return ""


# ── Endpoints ──────────────────────────────────────


@router.get("/stats", response_model=DataStats)
def get_stats():
    raw = Store().stats()
    cache = CacheStats(
        stock_count=raw["stock_count"],
        total_rows=raw["total_rows"],
        storage_bytes=raw["storage_bytes"],
        date_range_start=raw["date_range"]["start"],
        date_range_end=raw["date_range"]["end"],
        freq_stats=raw["freq_stats"],
    )
    return DataStats(cache=cache, database=_db_stats())


@router.post("/initialize", response_model=InitializeResult)
def initialize():
    fetcher = Fetcher()
    fetcher.stock_list()
    n = import_stocks()
    return InitializeResult(stock_count=n, message=f"已导入 {n} 只股票到 stocks 表")


@router.get("/stock-status", response_model=StockDataStatus)
def get_stock_status(code: str = Query(...)):
    store = Store()
    result = StockDataStatus(code=code, name=_stock_name(code, store))

    # 日线缓存
    try:
        if store.exists(code, "daily"):
            result.has_daily = True
            s, e, rows = _parquet_date_info(store._path(code, "daily"))
            result.daily_start = s
            result.daily_end = e
            result.daily_rows = rows
    except Exception:
        pass

    # 财务缓存
    try:
        if store.exists(code, "financial"):
            result.has_financial = True
            s, e, rows = _parquet_date_info(store._path(code, "financial"))
            result.financial_start = s
            result.financial_end = e
            result.financial_rows = rows
    except Exception:
        pass

    # 分钟级缓存
    for freq, attr in [("minute_60", "minute_60"), ("minute_30", "minute_30"), ("minute_15", "minute_15")]:
        try:
            if store.exists(code, freq):
                s, e, rows = _parquet_date_info(store._path(code, freq))
                setattr(getattr(result, attr), "exists", True)
                setattr(getattr(result, attr), "start", s)
                setattr(getattr(result, attr), "end", e)
                setattr(getattr(result, attr), "rows", rows)
        except Exception:
            pass

    # 自选股归属
    try:
        with SessionLocal() as s:
            from sqlalchemy import text
            rows = s.execute(
                text(
                    "SELECT w.name FROM watchlists w "
                    "JOIN watchlist_items wi ON w.id = wi.watchlist_id "
                    "WHERE wi.code = :code"
                ),
                {"code": code},
            ).fetchall()
            result.in_watchlist = [r[0] for r in rows]
    except Exception:
        pass

    return result


_VALID_FREQ = frozenset({"daily", "minute_60", "minute_30", "minute_15"})


@router.post("/refresh", response_model=RefreshResult)
def refresh(body: RefreshRequest):
    if body.freq not in _VALID_FREQ:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=400,
            content={"detail": f"未知频率: {body.freq}，有效值: {sorted(_VALID_FREQ)}"},
        )

    store = Store()
    codes = body.codes

    if body.force:
        codes = codes or store.codes(body.freq)
        for c in codes:
            store.delete(c, body.freq)

    if body.freq == "daily":
        if body.force:
            result = update_daily_data(codes=codes, discover_new=False, max_new=0)
        else:
            result = update_daily_data(
                codes=body.codes,
                discover_new=body.discover_new,
                max_new=body.max_new,
            )
    else:
        # minute_60 → "60", minute_30 → "30", minute_15 → "15"
        period = body.freq.split("_")[1]
        codes = codes or store.codes(body.freq)
        result = update_minute_data(codes=codes, period=period)

    errors = []
    details = result.get("details", {})
    for code, val in details.items():
        if val == -1:
            errors.append(RefreshError(code=code, error="fetch failed"))

    return RefreshResult(
        updated=result["updated"],
        failed=result["failed"],
        new_discovered=result["new_discovered"],
        errors=errors,
    )


# ── Internal helpers ───────────────────────────────

def _parquet_date_info(path) -> tuple[date | None, date | None, int]:
    """Read first/last rows+row count of a parquet file via pyarrow."""
    import pandas as pd
    import pyarrow.parquet as pq

    pf = pq.ParquetFile(path)
    idx_col = _find_index_column(pf) or "date"

    # Read only the index column from first & last row groups
    first_tbl = pf.read_row_group(0, columns=[idx_col])
    last_tbl = pf.read_row_group(pf.num_row_groups - 1, columns=[idx_col])

    # Convert the column to pandas Series directly (avoids pandas metadata mangling)
    first_series = first_tbl.column(idx_col).to_pandas()
    last_series = last_tbl.column(idx_col).to_pandas()

    values = pd.to_datetime(pd.concat([first_series, last_series]))
    return values.min().date(), values.max().date(), pf.metadata.num_rows


def _find_index_column(pf) -> str | None:
    """Extract the pandas index column name from parquet schema metadata."""
    import json
    meta = pf.schema_arrow.metadata
    if meta is None:
        return None
    try:
        pandas_meta = json.loads(meta.get(b"pandas", b"{}"))
        idx_cols = pandas_meta.get("index_columns", [])
        return idx_cols[0] if idx_cols else None
    except (json.JSONDecodeError, KeyError, IndexError):
        return None

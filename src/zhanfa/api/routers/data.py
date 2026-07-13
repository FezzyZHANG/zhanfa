"""Data management router — stats, stock status, and refresh."""

from __future__ import annotations

import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Query

from zhanfa.api.models import (
    STOCK_CODE_PATTERN,
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

logger = logging.getLogger(__name__)

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
        logger.warning(
            "Failed to read stock_list cache in _stock_name (code=%s)",
            code,
            exc_info=True,
        )
    with SessionLocal() as s:
        st = s.query(Stock).filter(Stock.code == code).first()
        if st:
            return st.name  # type: ignore[return-value]
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
        last_refreshed_at=raw.get("last_refreshed_at"),
    )
    return DataStats(cache=cache, database=_db_stats())


@router.post("/initialize", response_model=InitializeResult)
async def initialize():
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _initialize_data)


def _initialize_data() -> InitializeResult:
    fetcher = Fetcher()
    fetcher.stock_list()
    n = import_stocks()
    return InitializeResult(stock_count=n, message=f"已导入 {n} 只股票到 stocks 表")


@router.get("/stock-status", response_model=StockDataStatus)
def get_stock_status(
    code: Annotated[str, Query(pattern=STOCK_CODE_PATTERN)],
):
    store = Store()
    result = StockDataStatus(code=code, name=_stock_name(code, store))

    # 日线缓存
    try:
        if store.exists(code, "daily"):
            result.has_daily = True
            info = store.date_range(code, "daily") or {}
            result.daily_start = info.get("start")
            result.daily_end = info.get("end")
            result.daily_rows = info.get("rows", 0)
            result.daily_cached_at = store.mtime(code, "daily")
            metadata = store.load_metadata(code, "daily") or {}
            provider = metadata.get("provider")
            adjust = metadata.get("adjust")
            request_count = metadata.get("request_count")
            retry_count = metadata.get("retry_count")
            result.daily_provider = str(provider) if provider is not None else None
            result.daily_adjust = str(adjust) if adjust is not None else None
            result.daily_request_count = (
                int(request_count) if isinstance(request_count, int) else None
            )
            result.daily_retry_count = (
                int(retry_count) if isinstance(retry_count, int) else None
            )
    except Exception:
        logger.warning(
            "Failed to read daily cache for stock-status (code=%s)", code, exc_info=True
        )
    try:
        if store.exists(code, "financial"):
            result.has_financial = True
            info = store.date_range(code, "financial") or {}
            result.financial_start = info.get("start")
            result.financial_end = info.get("end")
            result.financial_rows = info.get("rows", 0)
            result.financial_cached_at = store.mtime(code, "financial")
    except Exception:
        logger.warning(
            "Failed to read financial cache for stock-status (code=%s)",
            code,
            exc_info=True,
        )
    for freq, attr in [
        ("minute_60", "minute_60"),
        ("minute_30", "minute_30"),
        ("minute_15", "minute_15"),
    ]:
        try:
            if store.exists(code, freq):
                info = store.date_range(code, freq) or {}
                setattr(getattr(result, attr), "exists", True)
                setattr(getattr(result, attr), "start", info.get("start"))
                setattr(getattr(result, attr), "end", info.get("end"))
                setattr(getattr(result, attr), "rows", info.get("rows", 0))
                setattr(getattr(result, attr), "cached_at", store.mtime(code, freq))
        except Exception:
            logger.warning(
                "Failed to read %s cache for stock-status (code=%s)",
                freq,
                code,
                exc_info=True,
            )
    try:
        with SessionLocal() as db_session:
            from sqlalchemy import text

            wl_rows = db_session.execute(
                text(
                    "SELECT w.name FROM watchlists w "
                    "JOIN watchlist_items wi ON w.id = wi.watchlist_id "
                    "WHERE wi.code = :code"
                ),
                {"code": code},
            ).fetchall()
            result.in_watchlist = [r[0] for r in wl_rows]
    except Exception:
        logger.exception(
            "Failed to query watchlist membership for stock-status (code=%s)", code
        )

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
        deferred=result.get("deferred", 0),
        providers=result.get("providers", {}),
        errors=errors,
    )

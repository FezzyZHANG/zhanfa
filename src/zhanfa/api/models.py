"""Pydantic models for API request/response schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


# ── Strategy ──────────────────────────────────────────

class ParamDef(BaseModel):
    type: str = "any"
    default: Any = None
    description: str = ""


class StrategyInfo(BaseModel):
    id: int
    name: str
    category: str
    description: str = ""
    params: dict[str, Any] = Field(default_factory=dict)
    code_ref: str | None = None
    created_at: str = ""
    updated_at: str = ""


class StrategyDetail(StrategyInfo):
    backtest_count: int = 0


class StrategyCreate(BaseModel):
    name: str
    category: str
    description: str = ""
    params: dict[str, Any] = Field(default_factory=dict)


class StrategyUpdate(BaseModel):
    params: dict[str, Any]


# ── Stock ─────────────────────────────────────────────

class StockInfo(BaseModel):
    code: str
    name: str
    exchange: str | None = None
    industry: str | None = None
    market_cap: float | None = None  # 总市值（亿元）
    listed_date: str | None = None


class StockListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[StockInfo]


class DailyDataPoint(BaseModel):
    date: date | datetime  # date for daily, datetime for minute-level
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float | None = None


class DailyResponse(BaseModel):
    code: str
    count: int
    data: list[DailyDataPoint]


class FinancialDataPoint(BaseModel):
    report_date: date
    net_profit: float | None = None
    revenue: float | None = None
    eps: float | None = None
    roe: float | None = None
    debt_ratio: float | None = None
    net_margin: float | None = None


class FinancialResponse(BaseModel):
    code: str
    years: int
    data: list[FinancialDataPoint]


class IndicatorSet(BaseModel):
    code: str
    date: date
    sma_20: float | None = None
    sma_60: float | None = None
    sma_120: float | None = None
    macd_dif: float | None = None
    macd_dea: float | None = None
    macd_bar: float | None = None
    rsi_14: float | None = None
    boll_upper: float | None = None
    boll_mid: float | None = None
    boll_lower: float | None = None


class IndicatorResponse(BaseModel):
    code: str
    count: int
    data: list[IndicatorSet]


# ── Watchlist ─────────────────────────────────────────

class WatchlistCreate(BaseModel):
    name: str


class WatchlistUpdate(BaseModel):
    name: str


class WatchlistItemDetail(BaseModel):
    code: str
    name: str = ""
    added_at: datetime | None = None
    notes: str | None = None


class WatchlistResponse(BaseModel):
    id: int
    name: str
    stock_count: int
    items: list[WatchlistItemDetail] = Field(default_factory=list)
    created_at: datetime


class WatchlistItemAdd(BaseModel):
    code: str
    notes: str | None = None


class WatchlistItemUpdate(BaseModel):
    notes: str | None = None


class WatchlistBatchAdd(BaseModel):
    codes: list[str]


class WatchlistBatchMove(BaseModel):
    target_watchlist_id: int
    codes: list[str]


class WatchlistBatchDelete(BaseModel):
    codes: list[str]


class BatchPreviewItem(BaseModel):
    code: str
    name: str
    in_current: bool
    in_other: list[str] = Field(default_factory=list)


class BatchPreviewResponse(BaseModel):
    preview: list[BatchPreviewItem]
    new_count: int
    existing_count: int


class DataStatus(BaseModel):
    has_daily: bool = False
    has_financial: bool = False
    daily_start: date | None = None
    daily_end: date | None = None
    financial_periods: int = 0


class QuoteItem(BaseModel):
    code: str
    name: str
    latest_price: float | None = None
    change_pct: float | None = None
    pe: float | None = None
    pb: float | None = None
    dividend_yield: float | None = None
    notes: str | None = None
    data_status: DataStatus | None = None
    data_freshness: str = "unknown"  # "cached" | "live" | "stale"


class WatchlistQuoteResponse(BaseModel):
    id: int
    name: str
    items: list[QuoteItem]


class StockSearchResult(BaseModel):
    code: str
    name: str


# ── Backtest ──────────────────────────────────────────

class CurvePoint(BaseModel):
    date: str
    value: float


class YearlyReturn(BaseModel):
    year: int
    value: float


class MonthlyReturn(BaseModel):
    year: int
    month: int
    value: float


class TradeRecord(BaseModel):
    date: str
    action: str  # buy / sell
    price: float
    quantity: float
    pnl: float | None = None


class BacktestRequest(BaseModel):
    code: str
    strategy: str
    start_date: str = "20200101"
    end_date: str = "21000101"
    initial_capital: float = 100_000
    commission: float = 0.0005
    slippage: float = 0.001
    strategy_id: int | None = None
    params: dict[str, Any] = Field(default_factory=dict)

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def _normalize_date(cls, v: str) -> str:
        """Accept both ISO YYYY-MM-DD and compact YYYYMMDD, normalize to YYYYMMDD."""
        if "-" in v:
            parts = v.strip().split("-")
            if len(parts) != 3:
                raise ValueError(f"Invalid date format: {v!r}, expected YYYY-MM-DD or YYYYMMDD")
            return "".join(p.zfill(2) for p in parts)
        return v


class BacktestMetrics(BaseModel):
    total_return: float
    ann_return: float
    ann_volatility: float
    sharpe: float
    sortino: float
    max_drawdown: float
    calmar: float
    win_rate: float
    years: float


class BacktestResult(BaseModel):
    task_id: str
    status: str  # pending | running | completed | failed
    request: BacktestRequest | None = None
    metrics: BacktestMetrics | None = None
    equity_curve: list[CurvePoint] | None = None
    drawdown_curve: list[CurvePoint] | None = None
    benchmark_curve: list[CurvePoint] | None = None
    yearly_returns: list[YearlyReturn] | None = None
    monthly_returns: list[MonthlyReturn] | None = None
    trades: list[TradeRecord] | None = None
    error: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class BacktestHistoryItem(BaseModel):
    task_id: str
    code: str
    strategy: str
    status: str
    total_return: float | None = None
    sharpe: float | None = None
    max_drawdown: float | None = None
    created_at: datetime


# ── Industry Comparison ───────────────────────────────

class IndustryPeer(BaseModel):
    code: str
    name: str
    roe: float = 0
    gross_margin: float = 0
    debt_ratio: float = 0
    revenue_growth: float = 0
    net_profit_growth: float = 0


class IndustryComparisonResponse(BaseModel):
    industry: str
    peers: list[IndustryPeer]


# ── Scheduler ─────────────────────────────────────────

class SchedulerJob(BaseModel):
    func: str
    time: str
    type: str


class SchedulerStatus(BaseModel):
    jobs: list[SchedulerJob]
    running: bool = False
    last_errors: list[dict] = Field(default_factory=list)
    next_run: dict[str, str | None] = Field(default_factory=dict)


class SchedulerTriggerRequest(BaseModel):
    action: str = "update_daily"  # update_daily | rebalance_index
    codes: list[str] | None = None
    index_code: str | None = None


# ── Data Stats ────────────────────────────────────────

class CacheStats(BaseModel):
    stock_count: int = 0
    total_rows: int = 0
    storage_bytes: int = 0
    date_range_start: date | None = None
    date_range_end: date | None = None
    freq_stats: dict[str, int] = Field(default_factory=dict)
    last_refreshed_at: datetime | None = None


class DBStats(BaseModel):
    stock_count: int = 0
    financial_count: int = 0
    watchlist_count: int = 0
    strategy_count: int = 0
    backtest_count: int = 0


class DataStats(BaseModel):
    cache: CacheStats
    database: DBStats


class MinuteCacheStatus(BaseModel):
    exists: bool = False
    start: date | None = None
    end: date | None = None
    rows: int = 0
    cached_at: datetime | None = None


class StockDataStatus(BaseModel):
    code: str
    name: str = ""
    has_daily: bool = False
    daily_start: date | None = None
    daily_end: date | None = None
    daily_rows: int = 0
    daily_cached_at: datetime | None = None
    has_financial: bool = False
    financial_start: date | None = None
    financial_end: date | None = None
    financial_rows: int = 0
    financial_cached_at: datetime | None = None
    minute_60: MinuteCacheStatus = Field(default_factory=MinuteCacheStatus)
    minute_30: MinuteCacheStatus = Field(default_factory=MinuteCacheStatus)
    minute_15: MinuteCacheStatus = Field(default_factory=MinuteCacheStatus)
    in_watchlist: list[str] = Field(default_factory=list)


# ── Data Refresh ──────────────────────────────────────

class RefreshRequest(BaseModel):
    codes: list[str] | None = None  # None = 刷新全部已缓存股票
    freq: str = "daily"
    force: bool = False
    discover_new: bool = True
    max_new: int = 50


class RefreshError(BaseModel):
    code: str
    error: str


class RefreshResult(BaseModel):
    updated: int = 0
    failed: int = 0
    new_discovered: int = 0
    errors: list[RefreshError] = Field(default_factory=list)


class InitializeResult(BaseModel):
    stock_count: int
    message: str

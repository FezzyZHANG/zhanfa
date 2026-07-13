"""多 Provider 数据获取与本地缓存编排。"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
import os
from threading import Lock

import pandas as pd

from .daily_providers import (
    DEFAULT_DAILY_END,
    DEFAULT_DAILY_START,
    DailyProvider,
    DailyProviderError,
    DailyProviderUnavailable,
    ProviderResult,
    build_daily_provider,
    call_akshare as _call_akshare,
    env_flag as _env_flag,
    env_int as _env_int,
    normalize_date,
    slice_daily_frame,
)
from .store import Store

logger = logging.getLogger(__name__)


def _env_ttl(key: str, default_hours: float | None) -> timedelta | None:
    """Read a TTL in hours from an env var, falling back to the default.

    Returns None when both env var is unset and default_hours is None (no expiry).
    """
    val = os.getenv(key)
    if val is not None:
        try:
            return timedelta(hours=float(val))
        except (TypeError, ValueError):
            pass
    if default_hours is not None:
        return timedelta(hours=default_hours)
    return None


@dataclass(frozen=True)
class DailyFetchStatus:
    provider: str
    elapsed_seconds: float
    request_count: int
    retry_count: int
    fallback: bool
    cache_hit: bool
    failure_reason: str | None = None


class Fetcher:
    """A股数据获取器，结果自动缓存到本地 parquet，支持 TTL 过期。

    TTL defaults (configurable via env vars):
      - CACHE_TTL_DAILY_HOURS (default 6): 日线行情
      - CACHE_TTL_INDEX_DAILY_HOURS (default 6): 指数日线
      - CACHE_TTL_STOCK_LIST_HOURS (default 24): 全A股列表
      - CACHE_TTL_INDEX_COMPONENTS_HOURS (default 24): 指数成分股
      - CACHE_TTL_INDUSTRY_STOCKS_HOURS (default 24): 行业成分股
      - CACHE_TTL_FINANCIAL_HOURS (default 720): 财务数据 (~30 days)
      - CACHE_TTL_MINUTE_HOURS (default 6): 分钟线行情
    """

    def __init__(
        self,
        store: Store | None = None,
        daily_provider: str | DailyProvider | None = None,
    ):
        self.store = store or Store()
        if daily_provider is None:
            daily_provider = os.getenv("ZHANFA_DAILY_PROVIDER", "tencent")
        self.daily_provider = (
            build_daily_provider(daily_provider)
            if isinstance(daily_provider, str)
            else daily_provider
        )
        fallback_name = "akshare" if self.daily_provider.name == "tencent" else "tencent"
        self.daily_fallback: DailyProvider | None = None
        if _env_flag("ZHANFA_DAILY_FALLBACK_ENABLED", True):
            try:
                self.daily_fallback = build_daily_provider(fallback_name)
            except DailyProviderUnavailable as exc:
                logger.warning(
                    "daily_provider_fallback_disabled provider=%s reason=%s",
                    fallback_name,
                    exc,
                )
        self.daily_overlap_days = _env_int(
            "ZHANFA_DAILY_INCREMENTAL_OVERLAP_DAYS", 7
        )
        self.qfq_full_refresh_days = _env_int(
            "ZHANFA_QFQ_FULL_REFRESH_DAYS", 30, 1
        )
        self.daily_max_concurrency = _env_int(
            "ZHANFA_DAILY_MAX_CONCURRENCY", 4, 1
        )
        self.daily_batch_size = _env_int("ZHANFA_DAILY_BATCH_SIZE", 50, 1)
        self.daily_batch_max_codes = _env_int(
            "ZHANFA_DAILY_BATCH_MAX_CODES", 500, 1
        )
        self._daily_status: dict[str, DailyFetchStatus] = {}
        self._status_lock = Lock()
        self.last_batch_errors: dict[str, str] = {}
        self.ttl_daily = _env_ttl("CACHE_TTL_DAILY_HOURS", 6)
        self.ttl_index_daily = _env_ttl("CACHE_TTL_INDEX_DAILY_HOURS", 6)
        self.ttl_stock_list = _env_ttl("CACHE_TTL_STOCK_LIST_HOURS", 24)
        self.ttl_index_components = _env_ttl("CACHE_TTL_INDEX_COMPONENTS_HOURS", 24)
        self.ttl_industry_stocks = _env_ttl("CACHE_TTL_INDUSTRY_STOCKS_HOURS", 24)
        self.ttl_financial = _env_ttl("CACHE_TTL_FINANCIAL_HOURS", 720)  # ~30 days
        self.ttl_minute = _env_ttl("CACHE_TTL_MINUTE_HOURS", 6)

    # ── 日线行情 ──────────────────────────────

    def daily(
        self,
        code: str,
        start: str = DEFAULT_DAILY_START,
        end: str = DEFAULT_DAILY_END,
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        """获取股票日线；缓存命中与网络结果都严格遵守请求区间。"""
        return self._daily_cached(
            code, start, end, adjust, freq="daily", is_index=False
        )

    def daily_batch(
        self,
        codes: list[str],
        start: str = DEFAULT_DAILY_START,
        end: str = DEFAULT_DAILY_END,
        adjust: str = "qfq",
    ) -> dict[str, pd.DataFrame]:
        """分批、限并发获取日线；单只失败不阻断已完成证券的缓存落盘。"""
        unique_codes = list(dict.fromkeys(codes))
        if len(unique_codes) > self.daily_batch_max_codes:
            raise ValueError(
                f"daily batch contains {len(unique_codes)} codes; hard limit is "
                f"{self.daily_batch_max_codes}"
            )
        result: dict[str, pd.DataFrame] = {}
        self.last_batch_errors = {}
        for offset in range(0, len(unique_codes), self.daily_batch_size):
            chunk = unique_codes[offset : offset + self.daily_batch_size]
            with ThreadPoolExecutor(max_workers=self.daily_max_concurrency) as executor:
                futures = {
                    executor.submit(self.daily, code, start, end, adjust): code
                    for code in chunk
                }
                for future in as_completed(futures):
                    code = futures[future]
                    try:
                        result[code] = future.result()
                    except Exception as exc:
                        self.last_batch_errors[code] = str(exc)
                        logger.error(
                            "daily_batch_failure code=%s reason=%s", code, exc
                        )
        return result

    # ── 指数行情 ─────────────────────────────

    def index_daily(
        self,
        code: str,
        start: str = DEFAULT_DAILY_START,
        end: str = DEFAULT_DAILY_END,
        adjust: str = "",
    ) -> pd.DataFrame:
        """获取指数日线，与股票日线共享 Provider 与缓存契约。"""
        return self._daily_cached(
            code, start, end, adjust, freq="index_daily", is_index=True
        )

    def daily_status(self, code: str) -> DailyFetchStatus | None:
        """返回本 Fetcher 实例最近一次证券日线读取的可观测状态。"""
        with self._status_lock:
            return self._daily_status.get(code)

    def _daily_cached(
        self,
        code: str,
        start: str,
        end: str,
        adjust: str,
        *,
        freq: str,
        is_index: bool,
    ) -> pd.DataFrame:
        start = normalize_date(start)
        end = normalize_date(end)
        raw_metadata = self.store.load_metadata(code, freq)
        metadata = raw_metadata if isinstance(raw_metadata, dict) else {}
        fresh = self.store.load(
            code,
            freq,
            max_age=self.ttl_index_daily if is_index else self.ttl_daily,
        )
        if (
            fresh is not None
            and not fresh.empty
            and self._cache_covers_start(fresh, metadata, start)
            and self._cache_adjust_matches(metadata, adjust, freq)
        ):
            result = slice_daily_frame(fresh, start, end)
            self._set_daily_status(
                code,
                DailyFetchStatus("cache", 0.0, 0, 0, False, True),
            )
            return result

        stale = fresh if fresh is not None else self.store.load(code, freq)
        if stale is not None and stale.empty:
            self.store.delete(code, freq)
            stale = None
        full_refresh = self._requires_full_refresh(
            stale, metadata, start, adjust, code, freq
        )
        fetch_start = start
        if stale is not None and not full_refresh:
            waterline = pd.Timestamp(stale.index.max()) - pd.Timedelta(
                days=self.daily_overlap_days
            )
            fetch_start = max(start, waterline.strftime("%Y%m%d"))

        provider_result, used_fallback = self._fetch_daily_provider(
            code, fetch_start, end, adjust, is_index=is_index
        )
        if (
            stale is not None
            and not full_refresh
            and adjust
            and metadata.get("provider") != provider_result.provider
        ):
            # 复权历史不能把不同来源片段静默拼接；回退后改为同源全量覆盖。
            provider = (
                self.daily_provider
                if self.daily_provider.name == provider_result.provider
                else self.daily_fallback
            )
            if provider is None:
                raise DailyProviderError(
                    "Adjusted cache requires a same-provider full refresh"
                )
            provider_result = provider.fetch(
                code, start, end, adjust, is_index=is_index
            )
            full_refresh = True

        if stale is not None and not full_refresh:
            combined = pd.concat([stale, provider_result.frame]).sort_index()
            combined = combined[~combined.index.duplicated(keep="last")]
        else:
            combined = provider_result.frame
        if combined.empty:
            raise DailyProviderError(
                f"Refusing to write empty {freq} cache for {code}"
            )
        self.store.save(code, combined, freq)
        updated_at = datetime.now(timezone.utc).isoformat()
        full_refresh_at = (
            updated_at if full_refresh else metadata.get("full_refresh_at", updated_at)
        )
        self.store.save_metadata(
            code,
            freq,
            {
                "provider": provider_result.provider,
                "adjust": adjust,
                "updated_at": updated_at,
                "full_refresh_at": full_refresh_at,
                "request_count": provider_result.request_count,
                "retry_count": provider_result.retry_count,
                "coverage_start": min(
                    start, str(metadata.get("coverage_start", start))
                ),
            },
        )
        status = DailyFetchStatus(
            provider_result.provider,
            provider_result.elapsed_seconds,
            provider_result.request_count,
            provider_result.retry_count,
            used_fallback,
            False,
        )
        self._set_daily_status(code, status)
        logger.info(
            "daily_fetch provider=%s code=%s elapsed=%.3f requests=%s retries=%s "
            "fallback=%s rows=%s",
            status.provider,
            code,
            status.elapsed_seconds,
            status.request_count,
            status.retry_count,
            status.fallback,
            len(provider_result.frame),
        )
        return slice_daily_frame(combined, start, end)

    def _fetch_daily_provider(
        self,
        code: str,
        start: str,
        end: str,
        adjust: str,
        *,
        is_index: bool,
    ) -> tuple[ProviderResult, bool]:
        try:
            return (
                self.daily_provider.fetch(
                    code, start, end, adjust, is_index=is_index
                ),
                False,
            )
        except Exception as primary_error:
            if self.daily_fallback is None:
                self._record_failure(code, self.daily_provider.name, primary_error)
                raise
            logger.warning(
                "daily_provider_fallback primary=%s fallback=%s code=%s reason=%s",
                self.daily_provider.name,
                self.daily_fallback.name,
                code,
                primary_error,
            )
            try:
                return (
                    self.daily_fallback.fetch(
                        code, start, end, adjust, is_index=is_index
                    ),
                    True,
                )
            except Exception as fallback_error:
                reason = (
                    f"primary {self.daily_provider.name}: {primary_error}; "
                    f"fallback {self.daily_fallback.name}: {fallback_error}"
                )
                self._record_failure(code, self.daily_fallback.name, reason)
                raise DailyProviderError(reason) from fallback_error

    def _requires_full_refresh(
        self,
        stale: pd.DataFrame | None,
        metadata: dict[str, object],
        start: str,
        adjust: str,
        code: str,
        freq: str,
    ) -> bool:
        if stale is None or stale.empty:
            return True
        if metadata.get("adjust") not in (None, adjust):
            return True
        if not self._cache_covers_start(stale, metadata, start):
            return True
        if adjust and metadata.get("provider") != self.daily_provider.name:
            return True
        if adjust:
            full_refresh_at = metadata.get("full_refresh_at")
            if not isinstance(full_refresh_at, str):
                return True
            try:
                refreshed = datetime.fromisoformat(full_refresh_at)
            except ValueError:
                return True
            if refreshed.tzinfo is None:
                refreshed = refreshed.replace(tzinfo=timezone.utc)
            age = datetime.now(timezone.utc) - refreshed
            if age >= timedelta(days=self.qfq_full_refresh_days):
                return True
        return False

    @staticmethod
    def _cache_covers_start(
        frame: pd.DataFrame, metadata: dict[str, object], start: str
    ) -> bool:
        coverage_start = metadata.get("coverage_start")
        if isinstance(coverage_start, str):
            try:
                return normalize_date(start) >= normalize_date(coverage_start)
            except ValueError:
                pass
        return pd.Timestamp(start) >= pd.Timestamp(frame.index.min())

    @staticmethod
    def _cache_adjust_matches(
        metadata: dict[str, object], adjust: str, freq: str
    ) -> bool:
        cached_adjust = metadata.get("adjust")
        if isinstance(cached_adjust, str):
            return cached_adjust == adjust
        # TICKET-065 之前的股票缓存默认前复权，指数缓存默认不复权。
        return (freq == "daily" and adjust == "qfq") or (
            freq == "index_daily" and adjust == ""
        )

    def _record_failure(self, code: str, provider: str, error: object) -> None:
        self._set_daily_status(
            code,
            DailyFetchStatus(provider, 0.0, 0, 0, False, False, str(error)),
        )
        logger.error(
            "daily_fetch_failure provider=%s code=%s reason=%s", provider, code, error
        )

    def _set_daily_status(self, code: str, status: DailyFetchStatus) -> None:
        with self._status_lock:
            self._daily_status[code] = status

    # ── 成分股 ──────────────────────────────

    def index_components(self, index_code: str = "000300") -> list[str]:
        """获取指数成分股列表，如沪深300（缓存一天）"""
        cache_key = f"components_{index_code}"
        cached = self.store.load(cache_key, "meta", max_age=self.ttl_index_components)
        if cached is not None:
            return cached["code"].tolist()

        df = _call_akshare("index_stock_cons_csindex", symbol=index_code)
        codes = df["成分券代码"].tolist()
        self.store.save(cache_key, pd.DataFrame({"code": codes}), "meta")
        return codes

    def stock_list(self) -> pd.DataFrame:
        """获取全A股列表（含代码、名称），缓存 24h 后自动刷新，坏缓存自动修复"""
        cached = self.store.load("stock_list", "meta", max_age=self.ttl_stock_list)
        if cached is not None and len(cached) >= 5000:
            return cached
        if cached is not None:
            self.store.delete("stock_list", "meta")  # 截断坏缓存删除后重新拉取

        df = _call_akshare("stock_info_a_code_name")
        df.columns = ["code", "name"]
        df["code"] = df["code"].astype(str).str.strip().str.zfill(6)
        self.store.save("stock_list", df, "meta")
        return df

    # ── 财务数据 ──────────────────────────────

    def financial(self, code: str) -> pd.DataFrame:
        """获取个股核心财务指标（ROE、EPS、资产负债率等），列名标准化为英文"""
        cached = self.store.load(code, "financial", max_age=self.ttl_financial)
        if cached is not None:
            return cached

        raw = _call_akshare(
            "stock_financial_abstract_ths", symbol=code, indicator="按报告期"
        )
        df = self._clean_financial(raw)
        self.store.save(code, df, "financial")
        return df

    # ── 内部工具 ──────────────────────────────

    # ── 分钟级行情 ───────────────────────────

    def minute(
        self, code: str, period: str = "60", adjust: str = "qfq"
    ) -> pd.DataFrame:
        """获取单只股票分钟级数据（15min/30min/1h 等），优先读缓存"""
        freq = f"minute_{period}"
        cached = self.store.load(code, freq, max_age=self.ttl_minute)
        if cached is not None:
            return cached

        sina_code = self._to_sina_code(code)
        df = _call_akshare(
            "stock_zh_a_minute", symbol=sina_code, period=period, adjust=adjust
        )
        df = self._clean_minute(df)
        self.store.save(code, df, freq)
        return df

    def minute_batch(
        self, codes: list[str], period: str = "60", adjust: str = "qfq"
    ) -> dict[str, pd.DataFrame]:
        """批量获取分钟级数据"""
        result = {}
        for code in codes:
            result[code] = self.minute(code, period, adjust)
        return result

    # ── 行业板块 ──────────────────────────────

    def industry_stocks(self, industry_name: str) -> pd.DataFrame:
        """获取指定行业板块的成分股列表"""
        cache_key = f"industry_{industry_name}"
        cached = self.store.load(cache_key, "meta", max_age=self.ttl_industry_stocks)
        if cached is not None:
            return cached

        try:
            df = _call_akshare("stock_board_industry_cons_em", symbol=industry_name)
            df = df.rename(columns={"代码": "code", "名称": "name"})
            if "code" in df.columns:
                df["code"] = df["code"].astype(str)
            self.store.save(cache_key, df[["code", "name"]], "meta")
            return df
        except Exception:
            return pd.DataFrame(columns=["code", "name"])

    # ── 内部工具 ──────────────────────────────

    @staticmethod
    def _to_sina_code(code: str) -> str:
        """将纯数字代码转为 Sina 格式: 60xxxx/68xxxx → sh, 其他 → sz"""
        if code.startswith(("60", "68")):
            return f"sh{code}"
        return f"sz{code}"

    @staticmethod
    def _clean_minute(df: pd.DataFrame) -> pd.DataFrame:
        """标准化 stock_zh_a_minute 返回的分钟线 DataFrame"""
        column_map = {
            "day": "date",
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "volume": "volume",
            "amount": "amount",
        }
        df = df.rename(columns={k: v for k, v in column_map.items() if k in df.columns})
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date")
            df.index.name = None
        # Sina 返回的 volume/amount 可能是字符串 (object/StringDtype)，统一转数值
        for col in ["volume", "amount"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.sort_index()
        return df

    def _clean_ohlcv(self, df: pd.DataFrame) -> pd.DataFrame:
        """将 akshare 返回的日线 DataFrame 标准化为 OHLCV 格式"""
        column_map = {
            "日期": "date",
            "开盘": "open",
            "最高": "high",
            "最低": "low",
            "收盘": "close",
            "成交量": "volume",
            "成交额": "amount",
            "换手率": "turnover",
        }
        df = df.rename(columns={k: v for k, v in column_map.items() if k in df.columns})
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date")
            df.index.name = None
        df = df.sort_index()
        return df

    def _clean_financial(self, df: pd.DataFrame) -> pd.DataFrame:
        """将 akshare 财务数据标准化：中文列名→英文、中文单位→float"""
        name_map = {
            "报告期": "report_date",
            "净利润": "net_profit",
            "净利润同比增长率": "net_profit_yoy",
            "扣非净利润": "net_profit_deducted",
            "扣非净利润同比增长率": "net_profit_deducted_yoy",
            "营业总收入": "revenue",
            "营业总收入同比增长率": "revenue_yoy",
            "基本每股收益": "eps",
            "每股净资产": "bvps",
            "每股资本公积金": "capital_reserve_ps",
            "每股未分配利润": "retained_earnings_ps",
            "每股经营现金流": "ocf_ps",
            "销售净利率": "net_margin",
            "净资产收益率": "roe",
            "净资产收益率-摊薄": "roe_diluted",
            "营业周期": "operating_cycle",
            "应收账款周转天数": "ar_turnover_days",
            "流动比率": "current_ratio",
            "速动比率": "quick_ratio",
            "保守速动比率": "conservative_quick_ratio",
            "产权比率": "equity_ratio",
            "资产负债率": "debt_ratio",
            "毛利率": "gross_margin",
            "股息率": "dividend_yield",
            "市盈率": "pe",
            "市净率": "pb",
        }
        df = df.rename(columns={k: v for k, v in name_map.items() if k in df.columns})
        if "report_date" in df.columns:
            df["report_date"] = pd.to_datetime(df["report_date"])
            df = df.set_index("report_date")
            df.index.name = None
        df = df.sort_index()
        for col in df.columns:
            df[col] = df[col].apply(_parse_financial_value)
        return df


def _parse_financial_value(val) -> float:
    """解析 akshare 财务值: '1.13亿' → 113000000, '38.08%' → 0.3808"""
    if isinstance(val, (int, float)):
        return float(val)
    if not isinstance(val, str):
        return float("nan")
    val = val.strip()
    if val == "False" or val == "":
        return float("nan")
    if "%" in val:
        return float(val.replace("%", "")) / 100
    if "亿" in val:
        return float(val.replace("亿", "")) * 1e8
    if "万" in val:
        return float(val.replace("万", "")) * 1e4
    return float(val)

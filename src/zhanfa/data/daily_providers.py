"""可切换的股票/指数日线数据 Provider。"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
import logging
import os
import random
from threading import BoundedSemaphore, Lock, RLock
import time
from typing import Callable, Protocol

import pandas as pd
import requests

logger = logging.getLogger(__name__)

DEFAULT_DAILY_START = "20180101"
DEFAULT_DAILY_END = "21000101"
DAILY_COLUMNS = ["open", "high", "low", "close", "volume", "amount", "turnover"]
TENCENT_VOLUME_TO_LOTS = 1.0
TENCENT_AMOUNT_TO_10K_CNY = 1.0
TENCENT_TURNOVER_TO_PERCENT = 1.0
TENCENT_DAILY_URL = (
    "https://proxy.finance.qq.com/ifzqgtimg/appstock/app/newfqkline/get"
)

_PROXY_ENV_VARS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "no_proxy",
)
_PROXY_ENV_LOCK = RLock()


def env_flag(key: str, default: bool = False) -> bool:
    value = os.getenv(key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(key: str, default: int, minimum: int = 0) -> int:
    try:
        return max(minimum, int(os.getenv(key, str(default))))
    except ValueError:
        return default


def env_float(key: str, default: float, minimum: float = 0.0) -> float:
    try:
        return max(minimum, float(os.getenv(key, str(default))))
    except ValueError:
        return default


@contextmanager
def akshare_proxy_env():
    """默认阻断 akshare 继承系统代理，允许环境变量显式启用。"""
    if env_flag("ZHANFA_AKSHARE_USE_PROXY", False):
        yield
        return

    with _PROXY_ENV_LOCK:
        saved = {key: os.environ[key] for key in _PROXY_ENV_VARS if key in os.environ}
        for key in _PROXY_ENV_VARS:
            os.environ.pop(key, None)
        try:
            yield
        finally:
            for key in _PROXY_ENV_VARS:
                os.environ.pop(key, None)
            os.environ.update(saved)


def call_akshare(func_name: str, *args, **kwargs):
    with akshare_proxy_env():
        import akshare as ak

        return getattr(ak, func_name)(*args, **kwargs)


class DailyProviderError(RuntimeError):
    """日线 Provider 的明确失败。"""


class DailyProviderResponseError(DailyProviderError):
    """上游返回无法满足契约。"""


class DailyProviderUnavailable(DailyProviderError):
    """Provider 熔断或暂时不可用。"""


class _RetryableProviderError(DailyProviderError):
    pass


@dataclass(frozen=True)
class ProviderResult:
    frame: pd.DataFrame
    provider: str
    request_count: int
    retry_count: int
    elapsed_seconds: float


class DailyProvider(Protocol):
    name: str

    def fetch(
        self,
        code: str,
        start: str,
        end: str,
        adjust: str,
        *,
        is_index: bool = False,
    ) -> ProviderResult: ...


def normalize_date(value: str) -> str:
    text = str(value).replace("-", "")
    if len(text) != 8 or not text.isdigit():
        raise ValueError(f"Invalid date: {value!r}; expected YYYYMMDD")
    datetime.strptime(text, "%Y%m%d")
    return text


def slice_daily_frame(df: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    """无论缓存或网络来源，均严格裁剪到调用方请求区间。"""
    start_ts = pd.Timestamp(normalize_date(start))
    end_ts = pd.Timestamp(normalize_date(end))
    if start_ts > end_ts:
        raise ValueError(f"start must not be after end: {start} > {end}")
    if df.empty:
        return df.copy()
    result = df.sort_index().loc[start_ts:end_ts].copy()
    result.index.name = None
    return result


def tencent_symbol(code: str, *, is_index: bool = False) -> str:
    """将 6 位证券代码映射为腾讯 sh/sz/bj 市场键。"""
    code = str(code).strip()
    if len(code) != 6 or not code.isdigit():
        raise ValueError(f"Invalid security code: {code!r}")
    if is_index:
        if code.startswith("399"):
            return f"sz{code}"
        return f"sh{code}"
    if code.startswith(("4", "8", "92")):
        return f"bj{code}"
    if code.startswith(("5", "6", "9")):
        return f"sh{code}"
    return f"sz{code}"


class TencentDailyProvider:
    """腾讯 Web K 线直连 Provider，包含超时、重试、限并发和熔断。"""

    name = "tencent"

    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
        jitter: Callable[[], float] = random.random,
    ) -> None:
        self.session = session or requests.Session()
        self.session.trust_env = env_flag("ZHANFA_TENCENT_USE_PROXY", False)
        self.connect_timeout = env_float("ZHANFA_DAILY_CONNECT_TIMEOUT", 3.05, 0.01)
        self.read_timeout = env_float("ZHANFA_DAILY_READ_TIMEOUT", 10.0, 0.01)
        self.max_retries = env_int("ZHANFA_DAILY_MAX_RETRIES", 3)
        self.backoff_base = env_float("ZHANFA_DAILY_BACKOFF_BASE", 0.5)
        self.circuit_threshold = env_int("ZHANFA_DAILY_CIRCUIT_FAILURES", 5, 1)
        self.circuit_reset_seconds = env_float(
            "ZHANFA_DAILY_CIRCUIT_RESET_SECONDS", 60.0, 0.01
        )
        self._sleep = sleep
        self._jitter = jitter
        self._semaphore = BoundedSemaphore(
            env_int("ZHANFA_DAILY_MAX_CONCURRENCY", 4, 1)
        )
        self._circuit_lock = Lock()
        self._consecutive_failures = 0
        self._circuit_opened_at: float | None = None

    def fetch(
        self,
        code: str,
        start: str,
        end: str,
        adjust: str,
        *,
        is_index: bool = False,
    ) -> ProviderResult:
        started = time.monotonic()
        start = normalize_date(start)
        end = normalize_date(end)
        if adjust not in {"", "qfq", "hfq"}:
            raise ValueError(f"Unsupported adjust mode: {adjust!r}")
        symbol = tencent_symbol(code, is_index=is_index)
        capped_end = min(end, date.today().strftime("%Y%m%d"))
        if start > capped_end:
            return ProviderResult(
                _empty_daily_frame(), self.name, 0, 0, time.monotonic() - started
            )

        frames: list[pd.DataFrame] = []
        request_count = 0
        retry_count = 0
        for year in range(int(start[:4]), int(capped_end[:4]) + 1):
            window_start = max(start, f"{year}0101")
            window_end = min(capped_end, f"{year}1231")
            frame, attempts = self._request_window(
                symbol, window_start, window_end, adjust
            )
            request_count += attempts
            retry_count += attempts - 1
            frames.append(frame)

        if not frames:
            result = _empty_daily_frame()
        else:
            result = pd.concat(frames).sort_index()
            result = result[~result.index.duplicated(keep="last")]
            result = slice_daily_frame(result, start, capped_end)
        if result.empty:
            raise DailyProviderResponseError(
                f"Tencent returned no rows for {symbol} in {start}..{capped_end}"
            )
        return ProviderResult(
            result,
            self.name,
            request_count,
            retry_count,
            time.monotonic() - started,
        )

    def _request_window(
        self, symbol: str, start: str, end: str, adjust: str
    ) -> tuple[pd.DataFrame, int]:
        self._check_circuit()
        params = {
            "param": (
                f"{symbol},day,{_hyphen_date(start)},{_hyphen_date(end)},640,{adjust}"
            )
        }
        attempts = 0
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            attempts += 1
            try:
                with self._semaphore:
                    response = self.session.get(
                        TENCENT_DAILY_URL,
                        params=params,
                        timeout=(self.connect_timeout, self.read_timeout),
                    )
                if response.status_code == 429 or response.status_code >= 500:
                    raise _RetryableProviderError(
                        f"Tencent HTTP {response.status_code} for {symbol}"
                    )
                if response.status_code >= 400:
                    raise DailyProviderResponseError(
                        f"Tencent HTTP {response.status_code} for {symbol}"
                    )
                try:
                    payload = response.json()
                except ValueError as exc:
                    raise _RetryableProviderError(
                        f"Tencent returned non-JSON content for {symbol}"
                    ) from exc
                frame = self._parse_payload(payload, symbol, adjust)
                self._record_success()
                return frame, attempts
            except (requests.Timeout, requests.ConnectionError, _RetryableProviderError) as exc:
                last_error = exc
                self._record_failure()
                if attempt >= self.max_retries:
                    break
                delay = self.backoff_base * (2**attempt) + self._jitter() * self.backoff_base
                logger.warning(
                    "daily_provider_retry provider=tencent symbol=%s retry=%s delay=%.3f reason=%s",
                    symbol,
                    attempt + 1,
                    delay,
                    exc,
                )
                self._sleep(delay)
            except DailyProviderError:
                self._record_failure()
                raise
        raise DailyProviderError(
            f"Tencent request failed for {symbol} after {attempts} attempts: {last_error}"
        ) from last_error

    @staticmethod
    def _parse_payload(payload: object, symbol: str, adjust: str) -> pd.DataFrame:
        if not isinstance(payload, dict):
            raise DailyProviderResponseError("Tencent response root is not an object")
        if payload.get("code") != 0:
            raise DailyProviderResponseError(
                f"Tencent business error code={payload.get('code')!r} msg={payload.get('msg')!r}"
            )
        data = payload.get("data")
        if not isinstance(data, dict) or symbol not in data:
            raise DailyProviderResponseError(
                f"Tencent response missing security key {symbol}"
            )
        security = data[symbol]
        if not isinstance(security, dict):
            raise DailyProviderResponseError(
                f"Tencent security payload is invalid for {symbol}"
            )
        response_key = {"": "day", "qfq": "qfqday", "hfq": "hfqday"}[adjust]
        rows = security.get(response_key)
        if not isinstance(rows, list) or not rows:
            raise DailyProviderResponseError(
                f"Tencent response missing non-empty {response_key} for {symbol}"
            )
        parsed: list[dict[str, object]] = []
        for row in rows:
            if not isinstance(row, list) or len(row) < 9:
                raise DailyProviderResponseError(
                    f"Tencent daily row has fewer than 9 fields for {symbol}"
                )
            parsed.append(
                {
                    "date": row[0],
                    "open": row[1],
                    "close": row[2],
                    "high": row[3],
                    "low": row[4],
                    # 腾讯原始单位：成交量=手，成交额=万元，换手率=百分数。
                    "volume": row[5],
                    "turnover": row[7],
                    "amount": row[8],
                }
            )
        frame = pd.DataFrame(parsed)
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
        for column in DAILY_COLUMNS:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        frame["volume"] *= TENCENT_VOLUME_TO_LOTS
        frame["amount"] *= TENCENT_AMOUNT_TO_10K_CNY
        frame["turnover"] *= TENCENT_TURNOVER_TO_PERCENT
        required = ["date", "open", "high", "low", "close", "volume"]
        if frame[required].isna().any().any():
            raise DailyProviderResponseError(
                f"Tencent response contains invalid required fields for {symbol}"
            )
        frame = frame.set_index("date")[DAILY_COLUMNS].sort_index()
        frame.index.name = None
        return frame

    def _check_circuit(self) -> None:
        with self._circuit_lock:
            if self._circuit_opened_at is None:
                return
            elapsed = time.monotonic() - self._circuit_opened_at
            if elapsed < self.circuit_reset_seconds:
                raise DailyProviderUnavailable(
                    f"Tencent circuit is open; retry after {self.circuit_reset_seconds - elapsed:.1f}s"
                )
            self._consecutive_failures = 0
            self._circuit_opened_at = None

    def _record_success(self) -> None:
        with self._circuit_lock:
            self._consecutive_failures = 0
            self._circuit_opened_at = None

    def _record_failure(self) -> None:
        with self._circuit_lock:
            self._consecutive_failures += 1
            if self._consecutive_failures >= self.circuit_threshold:
                self._circuit_opened_at = time.monotonic()


class AkshareDailyProvider:
    """当前 akshare 日线路径，用于回退与一键恢复。"""

    name = "akshare"

    def fetch(
        self,
        code: str,
        start: str,
        end: str,
        adjust: str,
        *,
        is_index: bool = False,
    ) -> ProviderResult:
        started = time.monotonic()
        start = normalize_date(start)
        end = normalize_date(end)
        try:
            if is_index:
                raw = call_akshare(
                    "stock_zh_index_daily",
                    symbol=tencent_symbol(code, is_index=True),
                )
            else:
                raw = call_akshare(
                    "stock_zh_a_hist",
                    symbol=code,
                    period="daily",
                    start_date=start,
                    end_date=end,
                    adjust=adjust,
                )
        except Exception as exc:
            raise DailyProviderError(f"akshare request failed for {code}: {exc}") from exc
        frame = _normalize_akshare_frame(raw)
        frame = slice_daily_frame(frame, start, end)
        if frame.empty:
            raise DailyProviderResponseError(
                f"akshare returned no rows for {code} in {start}..{end}"
            )
        return ProviderResult(
            frame, self.name, 1, 0, time.monotonic() - started
        )


def build_daily_provider(name: str) -> DailyProvider:
    normalized = name.strip().lower()
    if normalized == "tencent":
        _validate_tencent_usage()
        return TencentDailyProvider()
    if normalized == "akshare":
        return AkshareDailyProvider()
    raise ValueError(
        f"Unsupported daily provider {name!r}; expected 'tencent' or 'akshare'"
    )


def _validate_tencent_usage() -> None:
    usage = os.getenv("ZHANFA_USAGE_MODE", "research").strip().lower()
    if usage in {"commercial", "production", "public"} and not env_flag(
        "ZHANFA_TENCENT_RISK_ACCEPTED", False
    ):
        raise DailyProviderUnavailable(
            "Tencent direct data is restricted to local non-commercial research by default; "
            "complete an authorization review and set ZHANFA_TENCENT_RISK_ACCEPTED=true"
        )


def _normalize_akshare_frame(raw: pd.DataFrame) -> pd.DataFrame:
    name_map = {
        "日期": "date",
        "date": "date",
        "开盘": "open",
        "open": "open",
        "最高": "high",
        "high": "high",
        "最低": "low",
        "low": "low",
        "收盘": "close",
        "close": "close",
        "成交量": "volume",
        "volume": "volume",
        "成交额": "amount",
        "amount": "amount",
        "换手率": "turnover",
        "turnover": "turnover",
    }
    frame = raw.rename(columns={key: value for key, value in name_map.items() if key in raw})
    required = {"date", "open", "high", "low", "close", "volume"}
    missing = required - set(frame.columns)
    if missing:
        raise DailyProviderResponseError(
            f"akshare response missing columns: {sorted(missing)}"
        )
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    for column in DAILY_COLUMNS:
        if column not in frame:
            frame[column] = float("nan")
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    # 东方财富/Sina 成交额通常以元返回，统一换算为万元。
    frame["amount"] = frame["amount"] / 10_000
    frame = frame.set_index("date")[DAILY_COLUMNS].sort_index()
    frame = frame[~frame.index.duplicated(keep="last")]
    frame.index.name = None
    return frame


def _empty_daily_frame() -> pd.DataFrame:
    frame = pd.DataFrame(columns=DAILY_COLUMNS, dtype=float)
    frame.index = pd.DatetimeIndex([], name=None)
    return frame


def _hyphen_date(value: str) -> str:
    return f"{value[:4]}-{value[4:6]}-{value[6:]}"

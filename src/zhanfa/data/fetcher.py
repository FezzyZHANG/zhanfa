"""akshare 数据获取封装"""

from contextlib import contextmanager
import os
from datetime import timedelta
from threading import RLock

import pandas as pd

from .store import Store

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


def _env_flag(key: str, default: bool = False) -> bool:
    val = os.getenv(key)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


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


@contextmanager
def _akshare_proxy_env():
    """Run akshare calls without inherited proxy env by default."""
    if _env_flag("ZHANFA_AKSHARE_USE_PROXY", False):
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


def _call_akshare(func_name: str, *args, **kwargs):
    with _akshare_proxy_env():
        import akshare as ak

        return getattr(ak, func_name)(*args, **kwargs)


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

    def __init__(self, store: Store | None = None):
        self.store = store or Store()
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
        start: str = "20100101",
        end: str = "21000101",
        adjust: str = "qfq",
    ) -> pd.DataFrame:
        """获取单只股票日线（前复权），优先读缓存，超出 TTL 或坏缓存自动刷新"""
        cached = self.store.load(code, "daily", max_age=self.ttl_daily)
        if cached is not None and len(cached) >= 1:
            return cached
        if cached is not None:
            self.store.delete(code, "daily")  # 坏缓存删除后重新拉取

        df = _call_akshare(
            "stock_zh_a_hist",
            symbol=code, period="daily", start_date=start, end_date=end, adjust=adjust
        )
        df = self._clean_ohlcv(df)
        self.store.save(code, df, "daily")
        return df

    def daily_batch(
        self,
        codes: list[str],
        start: str = "20100101",
        end: str = "21000101",
        adjust: str = "qfq",
    ) -> dict[str, pd.DataFrame]:
        """批量获取日线"""
        result = {}
        for code in codes:
            result[code] = self.daily(code, start, end, adjust)
        return result

    # ── 指数行情 ─────────────────────────────

    def index_daily(
        self, code: str, start: str = "20100101", end: str = "21000101"
    ) -> pd.DataFrame:
        """获取指数日线（如 000300 沪深300）"""
        cached = self.store.load(code, "index_daily", max_age=self.ttl_index_daily)
        if cached is not None:
            return cached

        raw = _call_akshare(
            "stock_zh_index_daily",
            symbol=f"sh{code}" if code.startswith("000") else f"sz{code}",
        )

        # akshare 不同版本返回中/英列名，统一映射为英文
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
        }
        df = raw.rename(columns={k: v for k, v in name_map.items() if k in raw.columns})
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date")
            df.index.name = None
        df = df.sort_index()
        df = df.loc[start:end]  # type: ignore[misc]
        self.store.save(code, df, "index_daily")
        return df

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

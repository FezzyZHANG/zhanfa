"""数据处理管线 - 清洗、对齐、特征计算"""

import pandas as pd
import numpy as np


class Pipeline:
    """数据清洗与预处理管线"""

    @staticmethod
    def clean(df: pd.DataFrame) -> pd.DataFrame:
        """基础清洗：volume/amount 数值化、去停牌（0成交量行）、去NaN、排序"""
        df = df.copy()
        # 分钟级数据 (Sina) 的 volume/amount 可能是字符串，统一转数值
        for col in ["volume", "amount"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        if "volume" in df.columns:
            df = df[df["volume"] > 0]
        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.dropna(subset=["open", "high", "low", "close"])
        df = df.sort_index()
        return df

    @staticmethod
    def align(multi: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, dict[str, pd.Series]]:
        """
        多标的对齐：统一交易日历，返回对齐后的 price DataFrame + returns dict
        multi: {code: df}，每个 df 必须有 'close' 列，index 为 date
        返回: (price_df, returns_dict)
        """
        closes = {}
        for code, df in multi.items():
            closes[code] = df["close"]

        price = pd.DataFrame(closes).sort_index()
        price = price.dropna(how="all")
        price = price.ffill()

        returns = price.pct_change()
        return price, {c: returns[c] for c in price.columns}

    @staticmethod
    def compute_returns(df: pd.DataFrame, price_col: str = "close") -> pd.Series:
        """计算收益率序列"""
        return df[price_col].pct_change()

    @staticmethod
    def add_simple_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """添加常用技术指标列到 DataFrame"""
        df = df.copy()
        close = df["close"]

        df["sma_20"] = close.rolling(20).mean()
        df["sma_60"] = close.rolling(60).mean()
        df["sma_120"] = close.rolling(120).mean()

        df["vol_sma_20"] = df["volume"].rolling(20).mean()

        high_n = close.rolling(20).max()
        low_n = close.rolling(20).min()
        df["channel_pct"] = (close - low_n) / (high_n - low_n)

        df["ret_1d"] = close.pct_change()
        df["ret_5d"] = close.pct_change(5)
        df["ret_20d"] = close.pct_change(20)

        df["volatility_20d"] = df["ret_1d"].rolling(20).std()
        df["atr_14"] = Pipeline._calc_atr(df, 14)

        df["high_20"] = high_n
        df["low_20"] = low_n

        return df

    @staticmethod
    def _calc_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        high, low, close = df["high"], df["low"], df["close"]
        prev_close = close.shift(1)
        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs()
        ], axis=1).max(axis=1)
        return tr.ewm(span=period, adjust=False).mean()

    @staticmethod
    def train_test_split(df: pd.DataFrame, split_date: str) -> tuple[pd.DataFrame, pd.DataFrame]:
        """按时点切分训练集和测试集"""
        return df.loc[:split_date], df.loc[split_date:]

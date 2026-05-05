"""常用技术指标——纯函数，输入输出均为 pd.Series"""

import numpy as np
import pandas as pd


def sma(series: pd.Series, period: int) -> pd.Series:
    """简单移动均线"""
    return series.rolling(period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    """指数移动均线"""
    return series.ewm(span=period, adjust=False).mean()


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """MACD 指标"""
    ema_fast = ema(close, fast)
    ema_slow = ema(close, slow)
    dif = ema_fast - ema_slow
    dea = ema(dif, signal)
    bar = 2 * (dif - dea)
    return pd.DataFrame({"dif": dif, "dea": dea, "bar": bar}, index=close.index)


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """RSI 相对强弱指标"""
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def bollinger(close: pd.Series, period: int = 20, std: float = 2.0) -> pd.DataFrame:
    """布林带"""
    mid = sma(close, period)
    std_dev = close.rolling(period).std()
    return pd.DataFrame({"upper": mid + std * std_dev, "mid": mid, "lower": mid - std * std_dev}, index=close.index)


def donchian(high: pd.Series, low: pd.Series, period: int = 20) -> pd.DataFrame:
    """唐奇安通道"""
    return pd.DataFrame({
        "upper": high.rolling(period).max(),
        "mid": (high.rolling(period).max() + low.rolling(period).min()) / 2,
        "lower": low.rolling(period).min(),
    }, index=high.index)


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """ATR 平均真实波幅"""
    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


def highest(series: pd.Series, period: int) -> pd.Series:
    """N 期内最高值"""
    return series.rolling(period).max()


def lowest(series: pd.Series, period: int) -> pd.Series:
    """N 期内最低值"""
    return series.rolling(period).min()

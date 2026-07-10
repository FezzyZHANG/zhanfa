"""Indicator function tests."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from zhanfa.strategies.indicators import atr, bollinger, donchian, ema, highest, lowest, macd, rsi, sma


def test_sma_and_ema_known_values():
    s = pd.Series([1.0, 2.0, 3.0, 4.0])

    sma_result = sma(s, 2)
    assert np.isnan(sma_result.iloc[0])
    assert sma_result.iloc[1:].tolist() == [1.5, 2.5, 3.5]
    assert ema(s, 2).iloc[-1] == pytest.approx(3.5185185185)


def test_macd_constant_price_is_zero_after_first_point():
    close = pd.Series([10.0] * 40)

    result = macd(close)

    assert result[["dif", "dea", "bar"]].fillna(0).abs().sum().sum() == pytest.approx(0)


def test_rsi_handles_short_and_constant_series():
    short = pd.Series([1.0])
    constant = pd.Series([5.0] * 20)

    assert rsi(short).isna().all()
    assert rsi(constant).isna().all()


def test_bollinger_known_window():
    close = pd.Series([1.0, 2.0, 3.0])

    result = bollinger(close, period=2, std=2)

    assert result["mid"].iloc[-1] == pytest.approx(2.5)
    assert result["upper"].iloc[-1] == pytest.approx(3.9142135624)
    assert result["lower"].iloc[-1] == pytest.approx(1.0857864376)


def test_donchian_highest_lowest_known_values():
    high = pd.Series([1.0, 3.0, 2.0, 5.0])
    low = pd.Series([0.0, 1.0, -1.0, 2.0])

    channel = donchian(high, low, period=2)

    assert np.isnan(channel["upper"].iloc[0])
    assert np.isnan(channel["lower"].iloc[0])
    assert channel["upper"].iloc[1:].tolist() == [3.0, 3.0, 5.0]
    assert channel["lower"].iloc[1:].tolist() == [0.0, -1.0, -1.0]
    assert highest(high, 2).iloc[1:].tolist() == [3.0, 3.0, 5.0]
    assert lowest(low, 2).iloc[1:].tolist() == [0.0, -1.0, -1.0]


def test_atr_known_values():
    high = pd.Series([10.0, 12.0, 11.0])
    low = pd.Series([8.0, 9.0, 9.0])
    close = pd.Series([9.0, 10.0, 10.0])

    result = atr(high, low, close, period=2)

    assert result.iloc[0] == pytest.approx(2.0)
    assert result.iloc[1] == pytest.approx(2.6666666667)
    assert result.iloc[2] == pytest.approx(2.2222222222)


def test_indicators_preserve_nan_inputs():
    s = pd.Series([1.0, np.nan, 3.0, 4.0])

    assert sma(s, 2).isna().iloc[1]
    assert highest(s, 2).isna().iloc[1]

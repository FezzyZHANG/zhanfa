"""回测引擎单元测试"""

import numpy as np
import pandas as pd
import pytest

import zhanfa.backtest.engine as engine
from zhanfa.backtest.engine import (
    run_backtest,
    run_portfolio_backtest,
    compare_strategies,
)


class TestRunBacktest:
    def test_basic(self):
        dates = pd.date_range("2024-01-01", periods=200, freq="B")
        price = pd.Series(np.cumsum(np.random.randn(200) * 0.5) + 100, index=dates)
        signals = pd.Series(True, index=dates)

        pf = run_backtest(price, signals)
        assert pf is not None
        stats = pf.stats()
        assert stats["Start Value"] == 100000

    def test_with_sl_stop(self):
        dates = pd.date_range("2024-01-01", periods=200, freq="B")
        price = pd.Series(np.cumsum(np.random.randn(200) * 0.5) + 100, index=dates)
        signals = pd.Series(True, index=dates)

        pf = run_backtest(price, signals, sl_stop=0.1)
        assert pf is not None

    def test_with_tp_stop(self):
        dates = pd.date_range("2024-01-01", periods=200, freq="B")
        rng = np.random.default_rng(42)
        price = pd.Series(np.cumsum(rng.standard_normal(200) * 0.5) + 100, index=dates)
        signals = pd.Series(True, index=dates)

        pf = run_backtest(price, signals, tp_stop=0.3)
        assert pf is not None

    def test_stop_params_are_passed_as_fractional_distances(self, monkeypatch):
        captured = {}

        def fake_from_signals(*args, **kwargs):
            captured.update(kwargs)
            return object()

        monkeypatch.setattr(engine.vbt.Portfolio, "from_signals", fake_from_signals)
        dates = pd.date_range("2024-01-01", periods=5, freq="B")
        price = pd.Series([100, 95, 89, 91, 92], index=dates)
        signals = pd.Series(True, index=dates)

        pf = run_backtest(price, signals, sl_stop=0.1, tp_stop=0.3)

        assert pf is not None
        assert captured["sl_stop"] == pytest.approx(0.1)
        assert captured["tp_stop"] == pytest.approx(0.3)

    def test_custom_params(self):
        dates = pd.date_range("2024-01-01", periods=100, freq="B")
        price = pd.Series(np.cumsum(np.random.randn(100) * 0.5) + 100, index=dates)
        signals = pd.Series(True, index=dates)

        pf = run_backtest(price, signals, initial_capital=200000, commission=0.001)
        assert pf is not None


class TestRunPortfolioBacktest:
    @pytest.fixture
    def multi_data(self):
        dates = pd.date_range("2024-01-01", periods=150, freq="B")
        rng = np.random.default_rng(42)
        prices = pd.DataFrame({
            "stock_a": np.cumsum(rng.standard_normal(150) * 0.5) + 100,
            "stock_b": np.cumsum(rng.standard_normal(150) * 0.5) + 50,
        }, index=dates)
        signals = pd.DataFrame(True, index=dates, columns=["stock_a", "stock_b"])
        return prices, signals

    def test_equal_weight(self, multi_data):
        prices, signals = multi_data
        pf = run_portfolio_backtest(prices, signals)
        assert pf is not None

    def test_custom_weights(self, multi_data):
        prices, signals = multi_data
        pf = run_portfolio_backtest(prices, signals, weights={"stock_a": 0.6, "stock_b": 0.4})
        assert pf is not None

    def test_stop_params_are_passed_as_fractional_distances(self, monkeypatch):
        captured = {}

        def fake_from_signals(*args, **kwargs):
            captured.update(kwargs)
            return object()

        monkeypatch.setattr(engine.vbt.Portfolio, "from_signals", fake_from_signals)
        dates = pd.date_range("2024-01-01", periods=5, freq="B")
        prices = pd.DataFrame({
            "stock_a": [100, 95, 89, 91, 92],
            "stock_b": [50, 55, 65, 66, 67],
        }, index=dates)
        signals = pd.DataFrame(True, index=dates, columns=["stock_a", "stock_b"])

        pf = run_portfolio_backtest(prices, signals, sl_stop=0.1, tp_stop=0.3)

        assert pf is not None
        assert captured["sl_stop"] == pytest.approx(0.1)
        assert captured["tp_stop"] == pytest.approx(0.3)

    def test_mismatched_columns_uses_intersection(self, multi_data):
        prices, signals = multi_data
        signals_extra = signals.copy()
        signals_extra["stock_c"] = True
        pf = run_portfolio_backtest(prices, signals_extra)
        assert pf is not None

    def test_no_common_columns_raises(self):
        dates = pd.date_range("2024-01-01", periods=10, freq="B")
        prices = pd.DataFrame({"a": [1] * 10}, index=dates)
        signals = pd.DataFrame({"b": [True] * 10}, index=dates)
        with pytest.raises(ValueError):
            run_portfolio_backtest(prices, signals)


class TestCompareStrategies:
    def test_basic(self):
        from zhanfa.strategies.base import BaseStrategy

        class MockA(BaseStrategy):
            name = "mock_a"

            def generate_signals(self, data):
                return pd.Series(True, index=data.index)

        class MockB(BaseStrategy):
            name = "mock_b"

            def generate_signals(self, data):
                return pd.Series(False, index=data.index)

        dates = pd.date_range("2024-01-01", periods=100, freq="B")
        price = pd.Series(np.cumsum(np.random.randn(100) * 0.5) + 100, index=dates)

        result = compare_strategies(price, [MockA(), MockB()])
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2

"""Backtest service tests."""

import asyncio
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from zhanfa.api.services.backtest_service import (
    _tasks,
    submit_backtest,
    get_task,
    get_history,
    compare_backtests,
)


@pytest.fixture(autouse=True)
def clear_tasks():
    """Clear in-memory task store before each test."""
    _tasks.clear()
    yield
    _tasks.clear()


class TestSubmitBacktest:
    def test_creates_pending_task(self):
        req = {
            "code": "000001",
            "strategy": "sma_cross",
            "start_date": "20240101",
            "end_date": "20250101",
        }
        task_id = submit_backtest(req)
        assert isinstance(task_id, str)
        assert len(task_id) == 8

        task = _tasks[task_id]
        assert task["status"] == "pending"
        assert task["request"] == req
        assert task["metrics"] is None
        assert task["error"] is None


class TestGetTask:
    def test_returns_task(self):
        task_id = submit_backtest({"code": "000001", "strategy": "sma_cross"})
        task = get_task(task_id)
        assert task["task_id"] == task_id

    def test_returns_none_for_missing(self):
        assert get_task("nonexist") is None


class TestGetHistory:
    def test_returns_sorted(self):
        submit_backtest({"code": "000001", "strategy": "sma_cross"})
        submit_backtest({"code": "600519", "strategy": "turtle"})
        history = get_history()
        assert len(history) == 2
        assert "code" in history[0]

    def test_empty(self):
        assert get_history() == []


class TestCompareBacktests:
    def test_filters_by_task_id(self):
        tid1 = submit_backtest({"code": "000001", "strategy": "sma_cross"})
        submit_backtest({"code": "600519", "strategy": "turtle"})
        result = compare_backtests([tid1])
        assert len(result) == 1
        assert result[0]["task_id"] == tid1

    def test_empty_ids_returns_all(self):
        submit_backtest({"code": "000001", "strategy": "sma_cross"})
        submit_backtest({"code": "600519", "strategy": "turtle"})
        result = compare_backtests([])
        assert len(result) == 2


class TestRunBacktestAsync:
    def test_runs_backtest(self):
        async def _run():
            req = {
                "code": "000001",
                "strategy": "sma_cross",
                "start_date": "20240101",
                "end_date": "20250101",
            }
            task_id = submit_backtest(req)

            mock_fetcher = MagicMock()
            dates = pd.date_range("2024-01-01", periods=100, freq="B")
            mock_df = pd.DataFrame({
                "open": [10.0] * 100, "high": [12.0] * 100,
                "low": [9.0] * 100, "close": [11.0 + i * 0.01 for i in range(100)],
                "volume": [10000] * 100,
            }, index=dates)

            mock_fetcher.daily.return_value = mock_df

            with patch("zhanfa.api.services.backtest_service.Fetcher", return_value=mock_fetcher):
                from zhanfa.api.services.backtest_service import run_backtest_async
                await run_backtest_async(task_id)

            task = get_task(task_id)
            assert task["status"] == "completed", task.get("error")
            assert task["metrics"] is not None

        asyncio.run(_run())


class TestExecuteBacktest:
    def test_computes_metrics(self):
        from zhanfa.api.services.backtest_service import _execute_backtest

        req = {
            "code": "000001",
            "strategy": "sma_cross",
            "start_date": "20240101",
            "end_date": "20250101",
            "params": {"fast": 5, "slow": 20},
        }

        dates = pd.date_range("2024-01-01", periods=200, freq="B")
        import numpy as np
        np.random.seed(42)
        price = 10 + np.cumsum(np.random.randn(200) * 0.1)
        mock_df = pd.DataFrame({
            "open": price * 0.99, "high": price * 1.02,
            "low": price * 0.98, "close": price,
            "volume": np.random.randint(1000, 10000, 200),
        }, index=dates)

        mock_fetcher = MagicMock()
        mock_fetcher.daily.return_value = mock_df

        with patch("zhanfa.api.services.backtest_service.Fetcher", return_value=mock_fetcher):
            result = _execute_backtest(req)

        assert "metrics" in result
        assert "equity_curve" in result
        assert "drawdown_curve" in result
        assert "yearly_returns" in result
        assert "monthly_returns" in result
        assert "trades" in result
        m = result["metrics"]
        assert "total_return" in m
        assert "sharpe" in m
        assert "max_drawdown" in m
        assert len(result["equity_curve"]) > 0
        assert len(result["drawdown_curve"]) > 0

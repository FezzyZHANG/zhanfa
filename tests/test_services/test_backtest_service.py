"""Backtest service tests — in-memory and DB persistence."""

import asyncio
import datetime
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
from zhanfa.db.models import BacktestResult


@pytest.fixture(autouse=True)
def clear_tasks():
    """Clear in-memory task store before each test."""
    _tasks.clear()
    yield
    _tasks.clear()


@pytest.fixture
def patched_db(db_session):
    """Patch backtest_service.SessionLocal to use isolated in-memory DB."""
    with patch("zhanfa.api.services.backtest_service.SessionLocal", return_value=db_session):
        yield db_session


class TestSubmitBacktest:
    def test_creates_pending_task(self, patched_db):
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

    def test_creates_db_record(self, patched_db, db_session):
        """submit_backtest persists a pending record to backtest_results table."""
        req = {
            "code": "000001",
            "strategy": "sma_cross",
            "start_date": "20240101",
            "end_date": "20250101",
        }
        task_id = submit_backtest(req)

        task = _tasks[task_id]
        assert task.get("db_id") is not None

        row = db_session.query(BacktestResult).filter_by(id=task["db_id"]).first()
        assert row is not None
        assert row.status == "pending"
        assert row.task_id == task_id
        assert row.stock_codes == ["000001"]


class TestGetTask:
    def test_returns_task(self, patched_db):
        task_id = submit_backtest({"code": "000001", "strategy": "sma_cross"})
        task = get_task(task_id)
        assert task["task_id"] == task_id

    def test_returns_none_for_missing(self, patched_db):
        assert get_task("nonexist") is None

    def test_falls_back_to_db(self, patched_db, db_session):
        """get_task looks up persisted tasks in DB when not in memory."""
        now = datetime.datetime.now()
        row = BacktestResult(
            task_id="db_task_1",
            strategy_id=1,
            stock_codes=["000001"],
            params={},
            start_date=datetime.date(2024, 1, 1),
            end_date=datetime.date(2025, 1, 1),
            metrics={"total_return": 0.15, "sharpe": 1.2},
            equity_curve=[{"date": "2024-06-01", "value": 1.1}],
            status="completed",
            created_at=now,
        )
        db_session.add(row)
        db_session.commit()

        task = get_task("db_task_1")
        assert task is not None
        assert task["task_id"] == "db_task_1"
        assert task["status"] == "completed"
        assert task["metrics"]["total_return"] == 0.15
        assert len(task["equity_curve"]) == 1


class TestGetHistory:
    def test_returns_sorted(self, patched_db):
        submit_backtest({"code": "000001", "strategy": "sma_cross"})
        submit_backtest({"code": "600519", "strategy": "turtle"})
        history = get_history()
        assert len(history) == 2
        assert "code" in history[0]

    def test_empty(self, patched_db):
        assert get_history() == []

    def test_merges_db_and_memory(self, patched_db, db_session):
        """get_history merges persisted DB records with in-memory tasks."""
        # Create a DB-persisted completed task
        row = BacktestResult(
            task_id="db_completed",
            strategy_id=1,
            stock_codes=["600519"],
            params={},
            start_date=datetime.date(2024, 1, 1),
            end_date=datetime.date(2025, 1, 1),
            metrics={"total_return": 0.20, "sharpe": 1.5},
            status="completed",
            created_at=datetime.datetime(2024, 6, 1),
        )
        db_session.add(row)
        db_session.commit()

        # Create an in-memory pending task
        submit_backtest({"code": "000001", "strategy": "sma_cross"})

        history = get_history()
        assert len(history) >= 2
        task_ids = [h["task_id"] for h in history]
        assert "db_completed" in task_ids

    def test_db_history_survives_clear(self, patched_db, db_session):
        """DB-persisted tasks remain after in-memory _tasks is cleared."""
        row = BacktestResult(
            task_id="survivor",
            strategy_id=1,
            stock_codes=["000001"],
            params={},
            start_date=datetime.date(2024, 1, 1),
            end_date=datetime.date(2025, 1, 1),
            metrics={"total_return": 0.10},
            status="completed",
            created_at=datetime.datetime(2024, 5, 1),
        )
        db_session.add(row)
        db_session.commit()

        # Clear in-memory tasks (simulating restart)
        _tasks.clear()

        history = get_history()
        db_task_ids = [h["task_id"] for h in history]
        assert "survivor" in db_task_ids


class TestCompareBacktests:
    def test_filters_by_task_id(self, patched_db):
        tid1 = submit_backtest({"code": "000001", "strategy": "sma_cross"})
        submit_backtest({"code": "600519", "strategy": "turtle"})
        result = compare_backtests([tid1])
        assert len(result) == 1
        assert result[0]["task_id"] == tid1

    def test_empty_ids_returns_all(self, patched_db):
        submit_backtest({"code": "000001", "strategy": "sma_cross"})
        submit_backtest({"code": "600519", "strategy": "turtle"})
        result = compare_backtests([])
        assert len(result) == 2


class TestRunBacktestAsync:
    def test_runs_backtest(self, patched_db):
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

    def test_updates_db_on_completion(self, patched_db, db_session):
        """run_backtest_async persists results to DB on success."""
        async def _run():
            req = {
                "code": "000001",
                "strategy": "sma_cross",
                "start_date": "20240101",
                "end_date": "20250101",
            }
            task_id = submit_backtest(req)
            db_id = _tasks[task_id]["db_id"]

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

            # Verify DB was updated
            row = db_session.query(BacktestResult).filter_by(id=db_id).first()
            assert row is not None
            assert row.status == "completed"
            assert row.metrics is not None
            assert "total_return" in (row.metrics or {})
            assert len(row.equity_curve or []) > 0

        asyncio.run(_run())

    def test_updates_db_on_failure(self, patched_db, db_session):
        """run_backtest_async records failure in DB."""
        async def _run():
            req = {
                "code": "000001",
                "strategy": "sma_cross",
                "start_date": "20240101",
                "end_date": "20250101",
            }
            task_id = submit_backtest(req)
            db_id = _tasks[task_id]["db_id"]

            # Cause a failure in Fetcher
            with patch("zhanfa.api.services.backtest_service.Fetcher",
                       side_effect=RuntimeError("Data fetch failed")):
                from zhanfa.api.services.backtest_service import run_backtest_async
                await run_backtest_async(task_id)

            task = _tasks[task_id]
            assert task["status"] == "failed"
            assert task["error"] == "Data fetch failed"

            # Verify DB was updated
            row = db_session.query(BacktestResult).filter_by(id=db_id).first()
            assert row is not None
            assert row.status == "failed"
            assert "error" in (row.metrics or {})

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

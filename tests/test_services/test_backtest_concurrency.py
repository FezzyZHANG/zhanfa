"""Backtest 并发访问安全性测试"""

import asyncio
import threading
from unittest.mock import patch

import pandas as pd
import pytest

from zhanfa.api.services.backtest_service import (
    _tasks,
    submit_backtest,
    run_backtest_async,
    get_task,
)


def _make_request(**overrides):
    return {
        "code": "000001",
        "strategy": "sma_cross",
        "start_date": "20240101",
        "end_date": "20240131",
        "initial_capital": 100_000,
        "commission": 0.0005,
        "slippage": 0.001,
        "strategy_id": None,
        "params": {"fast": 5, "slow": 20},
        **overrides,
    }


@pytest.fixture(autouse=True)
def _clean_tasks():
    """Ensure _tasks is clean before and after each test."""
    _tasks.clear()
    yield
    _tasks.clear()


class TestConcurrentSubmissions:
    @patch("zhanfa.api.services.backtest_service._execute_backtest")
    @patch("zhanfa.api.services.backtest_service.SessionLocal")
    def test_concurrent_submit_no_duplicate_task_ids(
        self, _mock_session, _mock_exec, db_session,
    ):
        """Multiple concurrent submits should produce unique task IDs."""
        _mock_exec.return_value = {"metrics": {}, "equity_curve": []}
        _mock_session.return_value = db_session

        requests = [
            _make_request(code=f"00000{i}", strategy="sma_cross")
            for i in range(1, 6)
        ]

        task_ids = [submit_backtest(req) for req in requests]
        assert len(task_ids) == len(set(task_ids)), "Task IDs must be unique"

        for tid in task_ids:
            assert tid in _tasks

    @patch("zhanfa.api.services.backtest_service._execute_backtest")
    @patch("zhanfa.api.services.backtest_service.SessionLocal")
    def test_concurrent_submit_with_mixed_strategies(
        self, _mock_session, _mock_exec, db_session,
    ):
        """Submissions with different strategies don't interfere."""
        _mock_exec.return_value = {"metrics": {}, "equity_curve": []}
        _mock_session.return_value = db_session

        t1 = submit_backtest(_make_request(strategy="sma_cross"))
        t2 = submit_backtest(_make_request(strategy="turtle"))
        t3 = submit_backtest(_make_request(strategy="rsi"))

        task1 = get_task(t1)
        task2 = get_task(t2)
        task3 = get_task(t3)

        assert task1["request"]["strategy"] == "sma_cross"
        assert task2["request"]["strategy"] == "turtle"
        assert task3["request"]["strategy"] == "rsi"

    def test_tasks_dict_thread_safety_basic(self):
        """Concurrent reads and writes to _tasks from threads."""
        N = 20

        def submit_and_read():
            tid = submit_backtest(_make_request(code="000001"))
            task = get_task(tid)
            assert task is not None
            assert task["status"] == "pending"

        threads = [threading.Thread(target=submit_and_read) for _ in range(N)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(_tasks) == N


class TestConcurrentExecution:
    @patch("zhanfa.api.services.backtest_service._execute_backtest")
    @patch("zhanfa.api.services.backtest_service.SessionLocal")
    def test_parallel_run_backtests(self, _mock_session, _mock_exec, db_session):
        """Running multiple backtests concurrently should not corrupt shared state."""
        _mock_exec.return_value = {
            "metrics": {"total_return": 0.1},
            "equity_curve": [],
            "drawdown_curve": [],
            "yearly_returns": [],
            "monthly_returns": [],
            "trades": [],
        }
        _mock_session.return_value = db_session

        task_ids = [
            submit_backtest(_make_request(code=f"00000{i}"))
            for i in range(1, 5)
        ]

        async def _run():
            await asyncio.gather(*[run_backtest_async(tid) for tid in task_ids])

        asyncio.run(_run())

        for tid in task_ids:
            task = get_task(tid)
            assert task is not None
            assert task["status"] == "completed", f"Task {tid} should be completed"

    @patch("zhanfa.api.services.backtest_service._execute_backtest")
    @patch("zhanfa.api.services.backtest_service.SessionLocal")
    def test_concurrent_submit_and_run(self, _mock_session, _mock_exec, db_session):
        """Interleaved submit and run should work correctly."""
        _mock_exec.return_value = {"metrics": {}, "equity_curve": []}
        _mock_session.return_value = db_session

        async def _submit_and_run():
            tid = submit_backtest(_make_request(code="000001"))
            await run_backtest_async(tid)
            return tid

        async def _run_all():
            return await asyncio.gather(*[_submit_and_run() for _ in range(10)])

        tids = asyncio.run(_run_all())

        for tid in tids:
            task = get_task(tid)
            assert task["status"] == "completed"

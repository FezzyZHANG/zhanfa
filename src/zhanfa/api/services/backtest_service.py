"""Backtest service — async task management wrapping the backtest engine."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

import pandas as pd

from zhanfa.data import Fetcher
from zhanfa.data.pipeline import Pipeline
from zhanfa.strategies.base import BaseStrategy
from zhanfa.backtest.engine import run_backtest_from_strategy
from zhanfa.backtest.metrics import compute_metrics
from zhanfa.api.services.strategy_service import create_strategy_instance

_tasks: dict[str, dict] = {}


def submit_backtest(request: dict) -> str:
    task_id = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc)
    _tasks[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "request": request,
        "metrics": None,
        "equity_curve": [],
        "drawdown_curve": [],
        "benchmark_curve": None,
        "yearly_returns": [],
        "monthly_returns": [],
        "trades": [],
        "error": None,
        "created_at": now,
        "completed_at": None,
    }
    return task_id


async def run_backtest_async(task_id: str) -> None:
    task = _tasks.get(task_id)
    if task is None:
        return

    task["status"] = "running"
    req = task["request"]

    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, _execute_backtest, req)
        task["metrics"] = result.get("metrics")
        task["equity_curve"] = result.get("equity_curve", [])
        task["drawdown_curve"] = result.get("drawdown_curve", [])
        task["benchmark_curve"] = result.get("benchmark_curve")
        task["yearly_returns"] = result.get("yearly_returns", [])
        task["monthly_returns"] = result.get("monthly_returns", [])
        task["trades"] = result.get("trades", [])
        task["status"] = "completed"
    except Exception as e:
        task["status"] = "failed"
        task["error"] = str(e)
    finally:
        task["completed_at"] = datetime.now(timezone.utc)


def get_task(task_id: str) -> dict | None:
    return _tasks.get(task_id)


def get_history() -> list[dict]:
    result = [_serialize_task(t) for t in _tasks.values()]
    return sorted(result, key=lambda x: x["created_at"], reverse=True)


def compare_backtests(ids: list[str]) -> list[dict]:
    all_tasks = [_serialize_task(t) for t in _tasks.values()]
    if not ids:
        return sorted(all_tasks, key=lambda x: x["created_at"], reverse=True)
    return [t for t in all_tasks if t["task_id"] in ids or t["strategy"] in ids]


def _serialize_task(t: dict) -> dict:
    m = t.get("metrics") or {}
    return {
        "task_id": t["task_id"],
        "code": t["request"]["code"],
        "strategy": t["request"]["strategy"],
        "status": t["status"],
        "total_return": m.get("total_return"),
        "sharpe": m.get("sharpe"),
        "max_drawdown": m.get("max_drawdown"),
        "created_at": t["created_at"],
    }


def _execute_backtest(req: dict) -> dict:
    fetcher = Fetcher()
    df = fetcher.daily(req["code"], start=req["start_date"], end=req["end_date"])
    df = Pipeline.clean(df)

    strategy: BaseStrategy = create_strategy_instance(req["strategy"], req.get("params", {}))

    pf = run_backtest_from_strategy(
        df,
        strategy,
        freq="d",
        initial_capital=req.get("initial_capital"),
        commission=req.get("commission"),
        slippage=req.get("slippage"),
    )

    equity = pf.value()
    metrics = compute_metrics(equity)

    # 提取净值曲线
    equity_curve = [{"date": str(d.date()), "value": round(float(v), 4)} for d, v in equity.items()]

    # 提取回撤曲线
    drawdown = pf.drawdown()
    drawdown_curve = [{"date": str(d.date()), "value": round(float(v), 4)} for d, v in drawdown.items()]

    # 年度收益
    yearly = equity.resample("YE").apply(lambda x: x.iloc[-1] / x.iloc[0] - 1)
    yearly_returns = [{"year": int(d.year), "value": round(float(v), 4)} for d, v in yearly.items()]

    # 月度收益
    monthly = equity.resample("ME").apply(lambda x: x.iloc[-1] / x.iloc[0] - 1)
    monthly_returns = [{"year": int(d.year), "month": int(d.month), "value": round(float(v), 4)} for d, v in monthly.items()]

    # 交易记录 — 每笔 round-trip 拆为 entry 和 exit 两条
    records = pf.trades.records
    trades_list = []
    if len(records) > 0:
        date_index = equity.index
        for _, row in records.iterrows():
            entry_i = int(row["entry_idx"])
            exit_i = int(row["exit_idx"])
            is_long = row["direction"] == 0
            # entry
            trades_list.append({
                "date": str(date_index[entry_i].date()),
                "action": "buy" if is_long else "sell",
                "price": round(float(row["entry_price"]), 2),
                "quantity": abs(int(row["size"])),
                "pnl": 0.0,
            })
            # exit (carries the PnL)
            trades_list.append({
                "date": str(date_index[exit_i].date()),
                "action": "sell" if is_long else "buy",
                "price": round(float(row["exit_price"]), 2),
                "quantity": abs(int(row["size"])),
                "pnl": round(float(row["pnl"]), 2),
            })

    return {
        "metrics": {k: float(v) if isinstance(v, (int, float)) else v for k, v in metrics.items()},
        "equity_curve": equity_curve,
        "drawdown_curve": drawdown_curve,
        "benchmark_curve": None,
        "yearly_returns": yearly_returns,
        "monthly_returns": monthly_returns,
        "trades": trades_list,
    }

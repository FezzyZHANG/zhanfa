"""Backtest service — async task management wrapping the backtest engine.

In-memory _tasks holds running/pending tasks. Completed/failed tasks are
persisted to backtest_results table so they survive restarts.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import date, datetime, timezone

import pandas as pd

from zhanfa.data import Fetcher
from zhanfa.data.pipeline import Pipeline
from zhanfa.strategies.base import BaseStrategy
from zhanfa.backtest.engine import run_backtest_from_strategy
from zhanfa.backtest.metrics import compute_metrics
from zhanfa.api.services.strategy_service import create_strategy_instance
from zhanfa.db.base import SessionLocal
from zhanfa.db.models import BacktestResult, Strategy

_tasks: dict[str, dict] = {}


def _parse_date(s: str) -> date:
    """Parse '20200101' or '2020-01-01' to date."""
    s = s.strip()
    if len(s) == 8:
        return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    return date.fromisoformat(s)


def _resolve_strategy_id(request: dict) -> int | None:
    """Resolve strategy_id from request, looking up by name/code_ref if needed."""
    strategy_id = request.get("strategy_id")
    if strategy_id:
        return strategy_id

    strategy_key = request.get("strategy", "")
    if not strategy_key:
        return None

    session = SessionLocal()
    try:
        row = (
            session.query(Strategy)
            .filter((Strategy.name == strategy_key) | (Strategy.code_ref == strategy_key))
            .first()
        )
        if not row:
            row = (
                session.query(Strategy)
                .filter(Strategy.code_ref.endswith(f".{strategy_key}"))
                .first()
            )
        return row.id if row else None
    finally:
        session.close()


def _create_db_record(task_id: str, request: dict, strategy_id: int | None) -> BacktestResult | None:
    session = SessionLocal()
    try:
        record = BacktestResult(
            task_id=task_id,
            strategy_id=strategy_id,
            stock_codes=[request["code"]],
            params=request.get("params", {}),
            start_date=_parse_date(request["start_date"]),
            end_date=_parse_date(request["end_date"]),
            metrics={},
            status="pending",
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return record
    except Exception:
        session.rollback()
        return None
    finally:
        session.close()


def _update_db_record(db_id: int, updates: dict) -> None:
    session = SessionLocal()
    try:
        row = session.query(BacktestResult).filter_by(id=db_id).first()
        if row is None:
            return
        for key, value in updates.items():
            setattr(row, key, value)
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


def submit_backtest(request: dict) -> str:
    task_id = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc)

    strategy_id = _resolve_strategy_id(request)
    db_record = _create_db_record(task_id, request, strategy_id)

    _tasks[task_id] = {
        "task_id": task_id,
        "db_id": db_record.id if db_record else None,
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

        if task.get("db_id"):
            _update_db_record(task["db_id"], {
                "metrics": task["metrics"],
                "equity_curve": task["equity_curve"],
                "drawdown_curve": task["drawdown_curve"],
                "benchmark_curve": task["benchmark_curve"],
                "yearly_returns": task["yearly_returns"],
                "monthly_returns": task["monthly_returns"],
                "trades": task["trades"],
                "status": "completed",
            })
    except Exception as e:
        task["status"] = "failed"
        task["error"] = str(e)

        if task.get("db_id"):
            _update_db_record(task["db_id"], {
                "metrics": {"error": str(e)},
                "status": "failed",
            })
    finally:
        task["completed_at"] = datetime.now(timezone.utc)


def get_task(task_id: str) -> dict | None:
    """Return task by id — checks memory first, then DB for persisted tasks."""
    task = _tasks.get(task_id)
    if task:
        return task

    return _get_task_from_db(task_id)


def _get_task_from_db(task_id: str) -> dict | None:
    session = SessionLocal()
    try:
        row = session.query(BacktestResult).filter_by(task_id=task_id).first()
        if row is None:
            return None
        return _db_record_to_task_dict(row)
    finally:
        session.close()


def get_history() -> list[dict]:
    """Return merged history — memory tasks + DB-persisted tasks, deduplicated."""
    memory_tasks = {t["task_id"]: t for t in _tasks.values()}
    db_tasks = _get_db_history()

    merged: dict[str, dict] = {}
    for t in db_tasks:
        merged[t["task_id"]] = t
    # Memory tasks take precedence (more current status)
    for tid, t in memory_tasks.items():
        merged[tid] = _serialize_task(t)

    return sorted(merged.values(), key=lambda x: x["created_at"], reverse=True)


def _get_db_history() -> list[dict]:
    session = SessionLocal()
    try:
        rows = session.query(BacktestResult).order_by(BacktestResult.created_at.desc()).all()
        return [_db_row_to_history_item(r) for r in rows]
    finally:
        session.close()


def compare_backtests(ids: list[str]) -> list[dict]:
    all_tasks = get_history()
    if not ids:
        return all_tasks
    return [t for t in all_tasks if t["task_id"] in ids or t["strategy"] in ids]


def _serialize_task(t: dict) -> dict:
    m = t.get("metrics") or {}
    return {
        "task_id": t["task_id"],
        "code": t["request"]["code"] if t.get("request") else "",
        "strategy": t["request"]["strategy"] if t.get("request") else "",
        "status": t["status"],
        "total_return": m.get("total_return"),
        "sharpe": m.get("sharpe"),
        "max_drawdown": m.get("max_drawdown"),
        "created_at": t["created_at"],
    }


def _db_row_to_history_item(row: BacktestResult) -> dict:
    m = row.metrics or {}
    ct = row.created_at or datetime.now(timezone.utc)
    if ct.tzinfo is None:
        ct = ct.replace(tzinfo=timezone.utc)
    return {
        "task_id": row.task_id or "",
        "code": row.stock_codes[0] if row.stock_codes else "",
        "strategy": _strategy_name_for(row.strategy_id),
        "status": row.status,
        "total_return": m.get("total_return"),
        "sharpe": m.get("sharpe"),
        "max_drawdown": m.get("max_drawdown"),
        "created_at": ct,
    }


def _db_record_to_task_dict(row: BacktestResult) -> dict:
    date_str = str(row.start_date).replace("-", "")
    end_str = str(row.end_date).replace("-", "")
    ct = row.created_at or datetime.now(timezone.utc)
    if ct.tzinfo is None:
        ct = ct.replace(tzinfo=timezone.utc)
    return {
        "task_id": row.task_id or "",
        "status": row.status,
        "request": {
            "code": row.stock_codes[0] if row.stock_codes else "",
            "strategy": _strategy_name_for(row.strategy_id),
            "start_date": date_str,
            "end_date": end_str,
            "params": row.params or {},
        },
        "metrics": row.metrics or {},
        "equity_curve": row.equity_curve or [],
        "drawdown_curve": row.drawdown_curve or [],
        "benchmark_curve": row.benchmark_curve,
        "yearly_returns": row.yearly_returns or [],
        "monthly_returns": row.monthly_returns or [],
        "trades": row.trades or [],
        "error": (row.metrics or {}).get("error"),
        "created_at": ct,
        "completed_at": ct,
    }


def _strategy_name_for(strategy_id: int | None) -> str:
    if not strategy_id:
        return ""
    session = SessionLocal()
    try:
        row = session.query(Strategy).filter_by(id=strategy_id).first()
        return row.name if row else ""
    finally:
        session.close()


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

    equity_curve = [{"date": str(d.date()), "value": round(float(v), 4)} for d, v in equity.items()]

    drawdown = pf.drawdown()
    drawdown_curve = [{"date": str(d.date()), "value": round(float(v), 4)} for d, v in drawdown.items()]

    yearly = equity.resample("YE").apply(lambda x: x.iloc[-1] / x.iloc[0] - 1)
    yearly_returns = [{"year": int(d.year), "value": round(float(v), 4)} for d, v in yearly.items()]

    monthly = equity.resample("ME").apply(lambda x: x.iloc[-1] / x.iloc[0] - 1)
    monthly_returns = [{"year": int(d.year), "month": int(d.month), "value": round(float(v), 4)} for d, v in monthly.items()]

    records = pf.trades.records
    trades_list = []
    if len(records) > 0:
        date_index = equity.index
        for _, row in records.iterrows():
            entry_i = int(row["entry_idx"])
            exit_i = int(row["exit_idx"])
            is_long = row["direction"] == 0
            trades_list.append({
                "date": str(date_index[entry_i].date()),
                "action": "buy" if is_long else "sell",
                "price": round(float(row["entry_price"]), 2),
                "quantity": abs(int(row["size"])),
                "pnl": 0.0,
            })
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

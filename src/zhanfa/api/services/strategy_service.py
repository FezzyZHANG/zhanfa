"""Strategy service — database-backed strategy CRUD."""

from __future__ import annotations

import importlib
from typing import Any

from zhanfa.db.base import SessionLocal
from zhanfa.db.models import Strategy, BacktestResult
from zhanfa.strategies.base import BaseStrategy


def list_strategies(
    category: str | None = None,
    search: str | None = None,
) -> list[dict[str, Any]]:
    session = SessionLocal()
    try:
        q = session.query(Strategy)
        if category:
            q = q.filter(Strategy.category == category)
        if search:
            pattern = f"%{search}%"
            q = q.filter(
                (Strategy.name.ilike(pattern)) | (Strategy.description.ilike(pattern))
            )
        rows = q.order_by(Strategy.id).all()
        return [_strategy_to_dict(r) for r in rows]
    finally:
        session.close()


def get_strategy(strategy_id: int) -> dict[str, Any] | None:
    session = SessionLocal()
    try:
        row = session.query(Strategy).filter_by(id=strategy_id).first()
        if row is None:
            return None
        return _strategy_to_dict(row)
    finally:
        session.close()


def get_strategy_results(strategy_id: int) -> list[dict[str, Any]]:
    session = SessionLocal()
    try:
        rows = (
            session.query(BacktestResult)
            .filter_by(strategy_id=strategy_id)
            .order_by(BacktestResult.created_at.desc())
            .all()
        )
        return [_backtest_to_dict(r) for r in rows]
    finally:
        session.close()


def create_strategy(
    name: str,
    category: str,
    description: str = "",
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    session = SessionLocal()
    try:
        row = Strategy(
            name=name,
            category=category,
            description=description,
            params=params or {},
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return _strategy_to_dict(row)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def update_strategy(strategy_id: int, params: dict[str, Any]) -> dict[str, Any] | None:
    session = SessionLocal()
    try:
        row = session.query(Strategy).filter_by(id=strategy_id).first()
        if row is None:
            return None
        row.params = params  # type: ignore[assignment]
        session.commit()
        session.refresh(row)
        return _strategy_to_dict(row)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_strategy_instance(
    strategy_key: str, params: dict[str, Any] | None = None
) -> BaseStrategy:
    """Instantiate a strategy class by name or DB code_ref.

    Tries DB lookup first (by name or code_ref suffix), registers discovered
    strategies if the DB is empty, then falls back to dynamic discovery.
    """
    code_ref = _resolve_code_ref(strategy_key)

    if code_ref:
        module_path, class_name = code_ref.rsplit(".", 1)
        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name)
        return cls(**(params or {}))

    raise ValueError(f"Unknown strategy: {strategy_key}")


def _resolve_code_ref(key: str) -> str | None:
    """Resolve a strategy key to a code_ref (module.ClassName)."""
    try:
        code_ref = _lookup_code_ref(key)
    except Exception:
        code_ref = None
    if code_ref:
        return code_ref

    try:
        from zhanfa.db.register_strategies import register_strategies

        register_strategies()
    except Exception:
        pass
    else:
        try:
            code_ref = _lookup_code_ref(key)
        except Exception:
            code_ref = None
        if code_ref:
            return code_ref

    from zhanfa.strategies.registry import discover_code_refs

    return _match_code_ref(key, discover_code_refs())


def _lookup_code_ref(key: str) -> str | None:
    session = SessionLocal()
    try:
        # Try exact match on name or code_ref
        row = (
            session.query(Strategy)
            .filter((Strategy.name == key) | (Strategy.code_ref == key))
            .first()
        )
        if row and row.code_ref:
            return str(row.code_ref)

        # Try suffix match on code_ref (e.g. "sma_cross" matches "...SMACross")
        if not row:
            row = (
                session.query(Strategy)
                .filter(Strategy.code_ref.endswith(f".{key}"))
                .first()
            )
        if row and row.code_ref:
            return str(row.code_ref)
    finally:
        session.close()

    return None


def _match_code_ref(key: str, code_refs: list[str]) -> str | None:
    for code_ref in code_refs:
        if code_ref == key:
            return code_ref
        # Module path suffix match: e.g. key "sma_cross" matches "...sma_cross.SMACross"
        module_path = code_ref.rsplit(".", 1)[0]  # zhanfa.strategies.trend.sma_cross
        if module_path.endswith(f".{key}"):
            return code_ref

    return None


def _strategy_to_dict(row: Strategy) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "category": row.category,
        "description": row.description or "",
        "params": row.params or {},
        "code_ref": row.code_ref,
        "created_at": row.created_at.isoformat() if row.created_at else "",
        "updated_at": row.updated_at.isoformat() if row.updated_at else "",
    }


def _backtest_to_dict(row: BacktestResult) -> dict[str, Any]:
    return {
        "id": row.task_id if row.task_id else str(row.id),
        "db_id": row.id,
        "strategy_id": row.strategy_id,
        "stock_codes": row.stock_codes or [],
        "params": row.params or {},
        "start_date": row.start_date.isoformat() if row.start_date else "",
        "end_date": row.end_date.isoformat() if row.end_date else "",
        "metrics": row.metrics or {},
        "equity_curve": row.equity_curve or [],
        "drawdown_curve": row.drawdown_curve or [],
        "benchmark_curve": row.benchmark_curve,
        "yearly_returns": row.yearly_returns or [],
        "monthly_returns": row.monthly_returns or [],
        "trades": row.trades or [],
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else "",
    }

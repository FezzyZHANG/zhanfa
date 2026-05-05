"""Auto-discover Python strategy classes and register to strategies table."""

import importlib
import inspect
import pkgutil
import re
from datetime import datetime
from typing import Any

from zhanfa.db.base import SessionLocal
from zhanfa.db.models import Strategy
from zhanfa.strategies.base import BaseStrategy


def _extract_params_from_cls(cls: type) -> dict[str, dict[str, Any]]:
    """Extract parameter metadata from a strategy class __init__ signature and docstring."""
    sig = inspect.signature(cls.__init__)
    doc = cls.__doc__ or ""

    params: dict[str, dict[str, Any]] = {}
    for name, param in sig.parameters.items():
        if name == "self":
            continue
        annotation = param.annotation if param.annotation is not inspect.Parameter.empty else None
        param_type = _annotation_to_str(annotation)
        default = param.default if param.default is not inspect.Parameter.empty else None
        desc = _extract_param_desc(doc, name)
        params[name] = {"type": param_type, "default": default, "description": desc}
    return params


def _annotation_to_str(annotation: Any) -> str:
    if annotation is None:
        return "any"
    if annotation is int:
        return "int"
    if annotation is float:
        return "float"
    if annotation is str:
        return "str"
    if annotation is bool:
        return "bool"
    return str(annotation)


def _extract_param_desc(doc: str, param_name: str) -> str:
    """Extract parameter description from docstring Parameters section."""
    pattern = rf"{param_name}[:：]\s*(.+?)(?:\n|$)"
    m = re.search(pattern, doc)
    return m.group(1).strip() if m else ""


def register_strategies(package_path: str = "zhanfa.strategies") -> list[str]:
    """Scan strategy package for BaseStrategy subclasses and upsert to database.

    Args:
        package_path: Strategy package path, e.g. "zhanfa.strategies"

    Returns:
        List of registered strategy class names.
    """
    package = importlib.import_module(package_path)
    registered: list[str] = []

    session = SessionLocal()
    try:
        for _, mod_name, is_pkg in pkgutil.walk_packages(
            package.__path__, prefix=package_path + "."
        ):
            if is_pkg:
                continue
            _register_module(importlib.import_module(mod_name), session, registered)

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    return registered


def _register_module(module, session, registered: list[str]) -> None:
    for name, obj in inspect.getmembers(module, inspect.isclass):
        if not issubclass(obj, BaseStrategy) or obj is BaseStrategy:
            continue
        _register_strategy(obj, session)
        registered.append(f"{obj.__module__}.{obj.__name__}")


def _register_strategy(cls, session) -> None:
    code_ref = f"{cls.__module__}.{cls.__name__}"

    # Infer category from module path: zhanfa.strategies.trend.SMACross → trend
    parts = cls.__module__.split(".")
    category = "unknown"
    for cat in ("trend", "momentum", "fundamental", "composite"):
        if cat in parts:
            category = cat
            break

    name = getattr(cls, "name", cls.__name__)
    description = (cls.__doc__ or "").strip()
    params = _extract_params_from_cls(cls)

    existing = session.query(Strategy).filter_by(code_ref=code_ref).first()
    if existing:
        existing.name = name
        existing.category = category
        existing.description = description
        existing.params = params
        existing.updated_at = datetime.now()
        return

    session.add(Strategy(
        name=name,
        category=category,
        description=description,
        params=params,
        code_ref=code_ref,
    ))

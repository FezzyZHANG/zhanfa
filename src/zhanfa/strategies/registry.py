"""内置策略注册表 — 自动发现 BaseStrategy 子类，提供统一 code_ref 查询。

DB 未初始化时 _resolve_code_ref 通过此表做 suffix 匹配回退，不再维护手写 fallback。
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil

from zhanfa.strategies.base import BaseStrategy


def discover_code_refs() -> list[str]:
    """Auto-discover all BaseStrategy subclass code_refs under zhanfa.strategies."""
    code_refs: list[str] = []
    package = importlib.import_module("zhanfa.strategies")

    for _, mod_name, is_pkg in pkgutil.walk_packages(
        package.__path__, prefix="zhanfa.strategies."
    ):
        if is_pkg:
            continue
        module = importlib.import_module(mod_name)
        for _name, obj in inspect.getmembers(module, inspect.isclass):
            if not issubclass(obj, BaseStrategy) or obj is BaseStrategy:
                continue
            code_refs.append(f"{obj.__module__}.{obj.__name__}")

    return code_refs


# Module-level — computed once at import time.
BUILTIN_CODE_REFS: list[str] = discover_code_refs()

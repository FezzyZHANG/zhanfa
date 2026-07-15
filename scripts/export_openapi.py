"""Deterministically export or verify the FastAPI OpenAPI contract."""

from __future__ import annotations

import argparse
import difflib
import json
from pathlib import Path
from typing import Any


def export_schema() -> dict[str, Any]:
    """Build the schema without starting a shared server or application lifespan."""
    from zhanfa.api import create_app

    return create_app(init_database=False, start_scheduler=False).openapi()


def render_schema(schema: dict[str, Any]) -> str:
    return json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def check_schema(path: Path) -> tuple[bool, str]:
    actual = render_schema(export_schema())
    try:
        expected = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return False, f"OpenAPI contract is missing: {path}"
    if expected == actual:
        return True, ""
    diff = "".join(
        difflib.unified_diff(
            expected.splitlines(keepends=True),
            actual.splitlines(keepends=True),
            fromfile=str(path),
            tofile="current FastAPI app.openapi()",
            n=3,
        )
    )
    return False, diff


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output", type=Path, help="write the current schema")
    mode.add_argument("--check", type=Path, help="compare against a committed schema")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(render_schema(export_schema()), encoding="utf-8")
        print(f"Wrote deterministic OpenAPI contract to {args.output}")
        return 0

    ok, details = check_schema(args.check)
    if not ok:
        print(details)
        print("Run `cd frontend && npm run contract:generate` after an intentional API change.")
        return 1
    print(f"OpenAPI contract matches {args.check}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

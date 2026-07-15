"""Start the isolated FastAPI process used by Playwright."""

from __future__ import annotations

import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _required_path(name: str) -> Path:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} must be set by the E2E launcher")
    return Path(value).resolve()


def _validate_runtime() -> tuple[Path, Path]:
    if os.environ.get("ZHANFA_E2E") != "1":
        raise RuntimeError("Refusing to start the fixture backend outside ZHANFA_E2E=1")
    runtime_dir = _required_path("E2E_RUNTIME_DIR")
    data_dir = _required_path("DATA_DIR")
    if not data_dir.is_relative_to(runtime_dir):
        raise RuntimeError(f"DATA_DIR must be inside E2E_RUNTIME_DIR: {data_dir}")
    database_url = os.environ.get("DATABASE_URL", "")
    if runtime_dir.as_posix().lower() not in database_url.replace("\\", "/").lower():
        raise RuntimeError("DATABASE_URL must point inside E2E_RUNTIME_DIR")
    runtime_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    return runtime_dir, data_dir


def main() -> None:
    runtime_dir, data_dir = _validate_runtime()
    host = os.environ.get("E2E_BACKEND_HOST", "127.0.0.1")
    port = int(os.environ.get("E2E_BACKEND_PORT", "8000"))

    from tests.support.e2e_runtime import create_e2e_app

    use_fixture_provider = os.environ.get("E2E_INCLUDE_LIVE") != "true"
    app = create_e2e_app(data_dir, use_fixture_provider=use_fixture_provider)
    print(
        "e2e_backend_start "
        f"runtime={runtime_dir} data={data_dir} database={os.environ['DATABASE_URL']} "
        f"provider={os.environ.get('ZHANFA_DAILY_PROVIDER')} "
        f"scheduler=disabled host={host} port={port}",
        flush=True,
    )

    import uvicorn

    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()

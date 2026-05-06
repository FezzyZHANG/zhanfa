"""Regression tests: importing zhanfa.api must not trigger database init or scheduler."""

import subprocess
import sys
import tempfile
from pathlib import Path


def test_import_zhanfa_api_does_not_create_db_file():
    """Pure import of zhanfa.api must not create a database file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_posix = Path(tmpdir).as_posix()
        code = f"""
import os
os.environ["DATABASE_URL"] = "sqlite:///{tmpdir_posix}/should_not_exist.db"
from zhanfa.api import app  # noqa: F401
db_path = r"{tmpdir_posix}/should_not_exist.db"
import pathlib
print("EXISTS" if pathlib.Path(db_path).exists() else "ABSENT")
"""
        r = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, cwd=Path(__file__).parent.parent.parent,
        )
        assert r.returncode == 0, f"Import failed:\n{r.stderr}"
        assert "ABSENT" in r.stdout, f"DB file was created on import:\n{r.stdout}\n{r.stderr}"


def test_import_zhanfa_api_does_not_start_scheduler_thread():
    """Pure import of zhanfa.api must not start a scheduler daemon thread."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_posix = Path(tmpdir).as_posix()
        code = f"""
import os
os.environ["DATABASE_URL"] = "sqlite:///{tmpdir_posix}/test.db"
from zhanfa.api import app  # noqa: F401
import threading
count = threading.active_count()
print(f"THREADS={{count}}")
"""
        r = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, cwd=Path(__file__).parent.parent.parent,
        )
        assert r.returncode == 0, f"Import failed:\n{r.stderr}"
        # Just importing the module should not start extra threads.
        # The main thread + any Python bookkeeping threads is normal (usually 1-2).
        # We check that we don't see a large spike which would indicate scheduler started.
        for line in r.stdout.strip().splitlines():
            if line.startswith("THREADS="):
                count = int(line.split("=")[1])
                assert count <= 2, f"Too many threads after import: {count}\n{r.stdout}"


def test_create_app_no_init_database_no_scheduler(monkeypatch):
    """create_app(init_database=False, start_scheduler=False) works with TestClient."""
    import importlib

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from fastapi.testclient import TestClient

    from zhanfa.api import create_app
    from zhanfa.db.base import Base, get_session

    from zhanfa.api.routers import data as data_router
    from zhanfa.api.services import strategy_service, backtest_service
    from zhanfa.db import base as db_base
    from zhanfa.db import import_data

    register_module = importlib.import_module("zhanfa.db.register_strategies")

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    TestingSessionLocal = sessionmaker(bind=engine)

    monkeypatch.setattr(db_base, "engine", engine)
    monkeypatch.setattr(db_base, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(strategy_service, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(backtest_service, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(data_router, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(import_data, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(register_module, "SessionLocal", TestingSessionLocal)

    Base.metadata.create_all(bind=engine)
    register_module.register_strategies()

    test_app = create_app(init_database=False, start_scheduler=False)

    def override_get_session():
        with TestingSessionLocal() as session:
            yield session

    test_app.dependency_overrides[get_session] = override_get_session
    try:
        with TestClient(test_app) as c:
            r = c.get("/api/health")
            assert r.status_code == 200
            assert r.json() == {"status": "ok"}

            # Scheduler should show not running since we disabled it
            r = c.get("/api/scheduler/status")
            assert r.status_code == 200
            data = r.json()
            assert data["running"] is False, f"Scheduler should not be running: {data}"
    finally:
        test_app.dependency_overrides.pop(get_session, None)
        Base.metadata.drop_all(bind=engine)
        engine.dispose()

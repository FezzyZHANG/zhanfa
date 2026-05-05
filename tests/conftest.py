"""Shared test fixtures."""

import importlib
import atexit
import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

_TEST_DB_PATH = Path(tempfile.gettempdir()) / f"zhanfa_pytest_{os.getpid()}.db"
if _TEST_DB_PATH.exists():
    _TEST_DB_PATH.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH.as_posix()}"


def _cleanup_test_db() -> None:
    try:
        if _TEST_DB_PATH.exists():
            _TEST_DB_PATH.unlink()
    except PermissionError:
        pass


atexit.register(_cleanup_test_db)

from zhanfa.db.base import Base, init_db
from zhanfa.db.register_strategies import register_strategies

init_db()
register_strategies()


@pytest.fixture
def db_session():
    """In-memory SQLite session with all tables created."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(monkeypatch):
    """FastAPI TestClient backed by a fresh isolated database."""
    from zhanfa.api import app
    from zhanfa.api.routers import data as data_router
    from zhanfa.api.services import strategy_service
    from zhanfa.db import base as db_base
    from zhanfa.db import import_data
    from zhanfa.db import models as _models

    register_module = importlib.import_module("zhanfa.db.register_strategies")

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    TestingSessionLocal = sessionmaker(bind=engine)

    from zhanfa.api.services import backtest_service

    monkeypatch.setattr(db_base, "engine", engine)
    monkeypatch.setattr(db_base, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(strategy_service, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(backtest_service, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(data_router, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(import_data, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(register_module, "SessionLocal", TestingSessionLocal)

    Base.metadata.create_all(bind=engine)
    register_module.register_strategies()

    def override_get_session():
        with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[db_base.get_session] = override_get_session
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.pop(db_base.get_session, None)
        Base.metadata.drop_all(bind=engine)
        engine.dispose()

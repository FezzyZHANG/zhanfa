"""zhanfa REST API — FastAPI application.

Start with:
    uv run uvicorn zhanfa.api:app --reload
"""

import os
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from zhanfa.api.routers import strategies, stocks, watchlists, backtest, scheduler, data
from zhanfa.db.base import init_db
from zhanfa.db.register_strategies import register_strategies


def _register_scheduler_tasks():
    """Register periodic tasks on the global scheduler."""
    from zhanfa.automation.scheduler import scheduler as sched
    from zhanfa.automation.workflows import (
        update_daily_data,
        update_minute_data,
        weekly_index_rebalance,
    )
    from zhanfa.data.store import Store

    # Daily data update at 15:30 (post market close)
    sched.register_func("update_daily_data", "15:30", "daily", update_daily_data)

    # Weekly index rebalance on Friday after market close
    def _weekly_rebalance():
        weekly_index_rebalance("000300")
    sched.register_func("weekly_index_rebalance", "16:00", "daily", _weekly_rebalance)

    # Minute data update for cached stocks at 15:30
    def _update_minute():
        store = Store()
        codes = store.codes("minute_60") + store.codes("minute_30") + store.codes("minute_15")
        codes = list(dict.fromkeys(codes))  # dedup
        if codes:
            for period in ["60", "30", "15"]:
                update_minute_data(codes, period)
    sched.register_func("update_minute_data", "15:45", "daily", _update_minute)

    # Start scheduler in background thread
    t = threading.Thread(target=sched.run_loop, daemon=True)
    t.start()


def _make_lifespan(init_database: bool, start_scheduler: bool):
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if init_database:
            init_db()
            registered = register_strategies()
            if registered:
                print(f"Registered {len(registered)} strategies: {registered}")
        if start_scheduler:
            _register_scheduler_tasks()
        yield
    return lifespan


def create_app(
    *,
    init_database: bool = True,
    start_scheduler: bool = True,
) -> FastAPI:
    """Create a FastAPI application instance.

    Args:
        init_database: If True, initialize DB tables and register strategies on startup.
        start_scheduler: If True, register and start background scheduler tasks on startup.
    """
    app = FastAPI(
        title="zhanfa API",
        description="A股策略回测与验证平台 API",
        version="0.1.0",
        lifespan=_make_lifespan(init_database, start_scheduler),
    )

    cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(strategies.router)
    app.include_router(stocks.router)
    app.include_router(watchlists.router)
    app.include_router(backtest.router)
    app.include_router(scheduler.router)
    app.include_router(data.router)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()

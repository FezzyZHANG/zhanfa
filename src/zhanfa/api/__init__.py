"""zhanfa REST API — FastAPI application.

Start with:
    uv run uvicorn zhanfa.api:app --reload
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from zhanfa.api.routers import strategies, stocks, watchlists, backtest, scheduler, data
from zhanfa.db.base import init_db
from zhanfa.db.register_strategies import register_strategies

init_db()


@asynccontextmanager
async def lifespan(app: FastAPI):
    registered = register_strategies()
    if registered:
        print(f"Registered {len(registered)} strategies: {registered}")
    yield


app = FastAPI(
    title="zhanfa API",
    description="A股策略回测与验证平台 API",
    version="0.1.0",
    lifespan=lifespan,
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

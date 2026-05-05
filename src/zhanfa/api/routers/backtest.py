from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from zhanfa.api.models import BacktestHistoryItem, BacktestRequest, BacktestResult
from zhanfa.api.services import backtest_service

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


@router.post("/run", response_model=BacktestResult)
async def submit_backtest(body: BacktestRequest, bg: BackgroundTasks):
    task_id = backtest_service.submit_backtest(body.model_dump())
    bg.add_task(backtest_service.run_backtest_async, task_id)
    task = backtest_service.get_task(task_id)
    return task


@router.get("/history", response_model=list[BacktestHistoryItem])
def get_backtest_history():
    return backtest_service.get_history()


@router.get("/compare", response_model=list[BacktestHistoryItem])
def compare_backtests(ids: str = Query("")):
    id_list = [s.strip() for s in ids.split(",") if s.strip()]
    return backtest_service.compare_backtests(id_list)


@router.get("/{task_id}", response_model=BacktestResult)
def get_backtest_status(task_id: str):
    task = backtest_service.get_task(task_id)
    if task is None:
        raise HTTPException(404, f"Task not found: {task_id}")
    return task

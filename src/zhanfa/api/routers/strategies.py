from fastapi import APIRouter, HTTPException, Query

from zhanfa.api.models import StrategyCreate, StrategyDetail, StrategyInfo, StrategyUpdate
from zhanfa.api.services import strategy_service

router = APIRouter(prefix="/api/strategies", tags=["strategies"])


@router.get("", response_model=list[StrategyInfo])
def list_strategies(
    category: str | None = Query(None),
    search: str | None = Query(None),
):
    return strategy_service.list_strategies(category=category, search=search)


@router.get("/{strategy_id}", response_model=StrategyDetail)
def get_strategy(strategy_id: int):
    s = strategy_service.get_strategy(strategy_id)
    if s is None:
        raise HTTPException(404, f"Strategy not found: {strategy_id}")
    results = strategy_service.get_strategy_results(strategy_id)
    s["backtest_count"] = len(results)
    return s


@router.get("/{strategy_id}/results")
def get_strategy_results(strategy_id: int):
    s = strategy_service.get_strategy(strategy_id)
    if s is None:
        raise HTTPException(404, f"Strategy not found: {strategy_id}")
    return strategy_service.get_strategy_results(strategy_id)


@router.post("", response_model=StrategyDetail, status_code=201)
def create_strategy(body: StrategyCreate):
    s = strategy_service.create_strategy(
        name=body.name,
        category=body.category,
        description=body.description,
        params=body.params,
    )
    s["backtest_count"] = 0
    return s


@router.put("/{strategy_id}", response_model=StrategyDetail)
def update_strategy(strategy_id: int, body: StrategyUpdate):
    s = strategy_service.update_strategy(strategy_id, body.params)
    if s is None:
        raise HTTPException(404, f"Strategy not found: {strategy_id}")
    results = strategy_service.get_strategy_results(strategy_id)
    s["backtest_count"] = len(results)
    return s

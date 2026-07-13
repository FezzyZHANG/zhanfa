from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query

from zhanfa.api.models import (
    STOCK_CODE_PATTERN,
    DailyResponse,
    FinancialResponse,
    IndicatorResponse,
    IndustryComparisonResponse,
    StockListResponse,
)
from zhanfa.api.services import stock_service
from zhanfa.data.daily_providers import DEFAULT_DAILY_END, DEFAULT_DAILY_START

router = APIRouter(prefix="/api/stocks", tags=["stocks"])

StockCodePath = Annotated[str, Path(pattern=STOCK_CODE_PATTERN)]


@router.get("", response_model=StockListResponse)
def list_stocks(page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200)):
    return stock_service.list_stocks(page=page, page_size=page_size)


@router.get("/industry/{industry}/comparison", response_model=IndustryComparisonResponse)
def get_industry_comparison(industry: str, limit: int = Query(20, ge=1, le=100)):
    return stock_service.get_industry_comparison(industry, limit=limit)


@router.get("/{code}", response_model=dict)
def get_stock(code: StockCodePath):
    result = stock_service.get_stock_meta(code)
    if result is None:
        raise HTTPException(404, f"Stock not found: {code}")
    return result


@router.get("/{code}/daily", response_model=DailyResponse)
def get_daily(
    code: StockCodePath,
    start: str = Query(DEFAULT_DAILY_START),
    end: str = Query(DEFAULT_DAILY_END),
    freq: str = Query("daily"),
):
    return stock_service.get_daily(code, start=start, end=end, freq=freq)


@router.get("/{code}/financial", response_model=FinancialResponse)
def get_financial(code: StockCodePath, years: int = Query(3, ge=1, le=20)):
    return stock_service.get_financial(code, years=years)


@router.get("/{code}/indicators", response_model=IndicatorResponse)
def get_indicators(
    code: StockCodePath,
    start: str = Query(DEFAULT_DAILY_START),
    end: str = Query(DEFAULT_DAILY_END),
):
    return stock_service.get_indicators(code, start=start, end=end)

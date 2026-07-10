from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from zhanfa.db.base import get_session
from zhanfa.api.models import (
    STOCK_CODE_PATTERN,
    StockSearchResult,
    WatchlistBatchAdd,
    WatchlistBatchDelete,
    WatchlistBatchMove,
    WatchlistCreate,
    WatchlistItemAdd,
    WatchlistItemUpdate,
    WatchlistQuoteResponse,
    WatchlistResponse,
    WatchlistUpdate,
)
from zhanfa.api.services import watchlist_service

router = APIRouter(prefix="/api/watchlists", tags=["watchlists"])

StockCodePath = Annotated[str, Path(pattern=STOCK_CODE_PATTERN)]


# ── Search (must be before /{wl_id} routes) ───────


@router.get("/search", response_model=list[StockSearchResult])
def search(q: str = Query("", min_length=1), db: Session = Depends(get_session)):
    return watchlist_service.search_stocks(db, q)


# ── Watchlist CRUD ────────────────────────────────


@router.get("", response_model=list[WatchlistResponse])
def list_watchlists(db: Session = Depends(get_session)):
    return watchlist_service.list_watchlists(db)


@router.post("", response_model=WatchlistResponse, status_code=201)
def create_watchlist(body: WatchlistCreate, db: Session = Depends(get_session)):
    return watchlist_service.create_watchlist(db, body.name)


@router.get("/{wl_id}", response_model=WatchlistResponse)
def get_watchlist(wl_id: int, db: Session = Depends(get_session)):
    result = watchlist_service.get_watchlist(db, wl_id)
    if result is None:
        raise HTTPException(404, f"Watchlist not found: {wl_id}")
    return result


@router.put("/{wl_id}", response_model=WatchlistResponse)
def update_watchlist(wl_id: int, body: WatchlistUpdate, db: Session = Depends(get_session)):
    result = watchlist_service.update_watchlist(db, wl_id, body.name)
    if result is None:
        raise HTTPException(404, f"Watchlist not found: {wl_id}")
    return result


@router.delete("/{wl_id}")
def delete_watchlist(wl_id: int, db: Session = Depends(get_session)):
    ok, msg = watchlist_service.delete_watchlist(db, wl_id)
    if not ok:
        raise HTTPException(400, msg)
    return {"detail": msg}


@router.get("/{wl_id}/quotes", response_model=WatchlistQuoteResponse)
def get_quotes(wl_id: int, db: Session = Depends(get_session)):
    result = watchlist_service.get_watchlist_quotes(db, wl_id)
    if result is None:
        raise HTTPException(404, f"Watchlist not found: {wl_id}")
    return result


@router.get("/{wl_id}/export")
def export_csv(wl_id: int, db: Session = Depends(get_session)):
    csv_content = watchlist_service.export_csv(db, wl_id)
    if csv_content is None:
        raise HTTPException(404, f"Watchlist not found: {wl_id}")
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=watchlist_{wl_id}.csv"},
    )


# ── Items ──────────────────────────────────────────


@router.post("/{wl_id}/items", response_model=WatchlistResponse)
def add_item(wl_id: int, body: WatchlistItemAdd, db: Session = Depends(get_session)):
    result = watchlist_service.add_item(db, wl_id, body.code, notes=body.notes)
    if result is None:
        raise HTTPException(404, f"Watchlist not found: {wl_id}")
    return result


@router.delete("/{wl_id}/items/{code}")
def remove_item(wl_id: int, code: StockCodePath, db: Session = Depends(get_session)):
    removed = watchlist_service.remove_item(db, wl_id, code)
    if not removed:
        raise HTTPException(404, f"Item not found: watchlist={wl_id}, code={code}")
    return {"detail": "removed"}


@router.put("/{wl_id}/items/{code}", response_model=WatchlistResponse)
def update_item_notes(wl_id: int, code: StockCodePath, body: WatchlistItemUpdate, db: Session = Depends(get_session)):
    result = watchlist_service.update_item_notes(db, wl_id, code, body.notes)
    if result is None:
        raise HTTPException(404, f"Item not found: watchlist={wl_id}, code={code}")
    return result


@router.post("/{wl_id}/items/batch", response_model=WatchlistResponse)
def batch_add_items(wl_id: int, body: WatchlistBatchAdd, db: Session = Depends(get_session)):
    result = watchlist_service.batch_add_items(db, wl_id, body.codes)
    if result is None:
        raise HTTPException(404, f"Watchlist not found: {wl_id}")
    return result


@router.post("/{wl_id}/items/batch-move", response_model=WatchlistResponse)
def batch_move_items(wl_id: int, body: WatchlistBatchMove, db: Session = Depends(get_session)):
    result = watchlist_service.batch_move_items(db, wl_id, body.target_watchlist_id, body.codes)
    if result is None:
        raise HTTPException(400, "Invalid operation")
    return result


@router.post("/{wl_id}/items/batch/preview")
def batch_add_preview(wl_id: int, body: WatchlistBatchAdd, db: Session = Depends(get_session)):
    result = watchlist_service.batch_add_preview(db, wl_id, body.codes)
    if result is None:
        raise HTTPException(404, f"Watchlist not found: {wl_id}")
    return result


@router.post("/{wl_id}/items/batch-delete")
def batch_delete_items(wl_id: int, body: WatchlistBatchDelete, db: Session = Depends(get_session)):
    removed = watchlist_service.batch_delete_items(db, wl_id, body.codes)
    return {"detail": f"removed {removed} items"}

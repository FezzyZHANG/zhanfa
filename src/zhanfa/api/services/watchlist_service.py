"""Watchlist service — CRUD for user watchlists via SQLAlchemy."""

from __future__ import annotations

import io
import csv as csv_module

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from zhanfa.db.models import Stock, Watchlist, WatchlistItem
from zhanfa.db.import_data import normalize_stock_code
from zhanfa.data import Fetcher


DEFAULT_WL_NAME = "默认"


# ── Watchlist CRUD ──────────────────────────────────


def list_watchlists(db: Session) -> list[dict]:
    _ensure_default(db)
    result = db.execute(
        select(Watchlist).options(joinedload(Watchlist.items).joinedload(WatchlistItem.stock))
        .order_by(Watchlist.created_at.asc())
    )
    watchlists = result.scalars().unique().all()
    return [_serialize_wl(w) for w in watchlists]


def create_watchlist(db: Session, name: str) -> dict:
    wl = Watchlist(name=name)
    db.add(wl)
    db.commit()
    db.refresh(wl)
    return _serialize_wl(wl)


def get_watchlist(db: Session, wl_id: int) -> dict | None:
    wl = db.get(Watchlist, wl_id)
    if wl is None:
        return None
    return _serialize_wl(wl)


def update_watchlist(db: Session, wl_id: int, name: str) -> dict | None:
    wl = db.get(Watchlist, wl_id)
    if wl is None:
        return None
    wl.name = name
    db.commit()
    db.refresh(wl)
    return _serialize_wl(wl)


def delete_watchlist(db: Session, wl_id: int) -> tuple[bool, str]:
    wl = db.get(Watchlist, wl_id)
    if wl is None:
        return False, "分组不存在"
    if wl.name == DEFAULT_WL_NAME:
        return False, "默认分组不可删除"
    db.delete(wl)
    db.commit()
    return True, "已删除"


# ── Items CRUD ─────────────────────────────────────


def add_item(db: Session, wl_id: int, code: str, notes: str | None = None) -> dict | None:
    code = normalize_stock_code(code)
    wl = db.get(Watchlist, wl_id)
    if wl is None:
        return None

    existing = [item for item in wl.items if item.code == code]
    if existing:
        if notes is not None:
            existing[0].notes = notes
            db.commit()
        db.refresh(wl)
        return _serialize_wl(wl)

    _ensure_stock(db, code)
    item = WatchlistItem(watchlist_id=wl_id, code=code, notes=notes)
    db.add(item)
    db.commit()
    db.refresh(wl)
    return _serialize_wl(wl)


def remove_item(db: Session, wl_id: int, code: str) -> bool:
    code = normalize_stock_code(code)
    wl = db.get(Watchlist, wl_id)
    if wl is None:
        return False

    for item in wl.items:
        if item.code == code:
            db.delete(item)
            db.commit()
            return True
    return False


def update_item_notes(db: Session, wl_id: int, code: str, notes: str | None) -> dict | None:
    code = normalize_stock_code(code)
    wl = db.get(Watchlist, wl_id)
    if wl is None:
        return None

    for item in wl.items:
        if item.code == code:
            item.notes = notes
            db.commit()
            db.refresh(wl)
            return _serialize_wl(wl)
    return None


def batch_add_items(db: Session, wl_id: int, codes: list[str]) -> dict | None:
    wl = db.get(Watchlist, wl_id)
    if wl is None:
        return None

    existing_codes = {item.code for item in wl.items}
    added = 0
    for code in codes:
        code = normalize_stock_code(code)
        if code and code not in existing_codes:
            _ensure_stock(db, code)
            db.add(WatchlistItem(watchlist_id=wl_id, code=code))
            existing_codes.add(code)
            added += 1

    db.commit()
    db.refresh(wl)
    return _serialize_wl(wl)


def batch_move_items(db: Session, from_wl_id: int, to_wl_id: int, codes: list[str]) -> dict | None:
    from_wl = db.get(Watchlist, from_wl_id)
    to_wl = db.get(Watchlist, to_wl_id)
    if from_wl is None or to_wl is None:
        return None

    existing_in_target = {item.code for item in to_wl.items}
    moved = 0
    for item in list(from_wl.items):
        if item.code in codes and item.code not in existing_in_target:
            item.watchlist_id = to_wl_id
            existing_in_target.add(item.code)
            moved += 1

    db.commit()
    db.refresh(from_wl)
    return _serialize_wl(from_wl)


def batch_add_preview(db: Session, wl_id: int, codes: list[str]) -> dict | None:
    """Preview what would happen if codes were added to a watchlist."""
    wl = db.get(Watchlist, wl_id)
    if wl is None:
        return None

    codes = list(dict.fromkeys([normalize_stock_code(c) for c in codes if str(c).strip()]))  # dedup preserve order
    current_codes = {item.code for item in wl.items}

    # Find names from DB
    names: dict[str, str] = {}
    if codes:
        try:
            from sqlalchemy import select as sa_select
            result = db.execute(sa_select(Stock).where(Stock.code.in_(codes)))
            for st in result.scalars():
                names[st.code] = st.name
        except Exception:
            pass

    # Check other watchlists
    preview = []
    new_count = 0
    existing_count = 0
    for code in codes:
        in_current = code in current_codes
        if in_current:
            existing_count += 1
        else:
            new_count += 1

        in_other = []
        try:
            from sqlalchemy import text
            rows = db.execute(
                text(
                    "SELECT w.name FROM watchlists w "
                    "JOIN watchlist_items wi ON w.id = wi.watchlist_id "
                    "WHERE wi.code = :code AND w.id != :wl_id"
                ),
                {"code": code, "wl_id": wl_id},
            ).fetchall()
            in_other = [r[0] for r in rows]
        except Exception:
            pass

        preview.append({
            "code": code,
            "name": names.get(code, ""),
            "in_current": in_current,
            "in_other": in_other,
        })

    return {"preview": preview, "new_count": new_count, "existing_count": existing_count}


def batch_delete_items(db: Session, wl_id: int, codes: list[str]) -> int:
    """Batch delete items from a watchlist. Returns count of removed items."""
    wl = db.get(Watchlist, wl_id)
    if wl is None:
        return 0

    code_set = {normalize_stock_code(code) for code in codes}
    removed = 0
    for item in list(wl.items):
        if item.code in code_set:
            db.delete(item)
            removed += 1

    db.commit()
    return removed


# ── Quotes ─────────────────────────────────────────


def _compute_freshness(store: "Store", code: str, freq: str) -> str:
    """Return a human-readable freshness label based on cache mtime."""
    mtime = store.mtime(code, freq)
    if mtime is None:
        return "unknown"
    from datetime import datetime, timezone
    age = datetime.now(timezone.utc) - mtime
    hours = age.total_seconds() / 3600
    if hours < 1:
        return "cached_1h"
    if hours < 24:
        return f"cached_{int(hours)}h"
    days = hours / 24
    if days < 7:
        return f"cached_{int(days)}d"
    return "stale"


def get_watchlist_quotes(db: Session, wl_id: int) -> dict | None:
    wl = db.get(Watchlist, wl_id)
    if wl is None:
        return None

    from zhanfa.data.store import Store

    store = Store()
    fetcher = Fetcher(store=store)
    codes = [item.code for item in wl.items]

    # Pre-load stock names from DB
    names: dict[str, str] = {}
    if codes:
        try:
            from sqlalchemy import select as sa_select
            result = db.execute(sa_select(Stock).where(Stock.code.in_(codes)))
            for st in result.scalars():
                names[st.code] = st.name
        except Exception:
            pass

    items = []
    for item in wl.items:
        code = item.code
        name = names.get(code, "")
        latest_price = None
        change_pct = None
        pe = None
        pb = None
        dividend_yield = None
        data_status = {
            "has_daily": False,
            "has_financial": False,
            "daily_start": None,
            "daily_end": None,
            "financial_periods": 0,
        }
        data_freshness = "unknown"

        # ── Daily price: cache-first ──
        try:
            close_info = store.last_close(code, "daily")
            if close_info:
                latest_price = float(close_info["close"])
                data_status["has_daily"] = True
                data_freshness = _compute_freshness(store, code, "daily")
                prev_close = close_info.get("prev_close")
                if prev_close and prev_close != 0:
                    change_pct = (latest_price - float(prev_close)) / float(prev_close)

                # Get date range from cache
                dr = store.date_range(code, "daily")
                if dr:
                    data_status["daily_start"] = dr.get("start")
                    data_status["daily_end"] = dr.get("end")
            else:
                # Fall back to live fetch
                df = fetcher.daily(code)
                if not df.empty:
                    latest = df.iloc[-1]
                    latest_price = float(latest["close"])
                    data_status["has_daily"] = True
                    data_freshness = "live"
                    if len(df) >= 2:
                        prev_close = float(df.iloc[-2]["close"])
                        if prev_close and prev_close != 0:
                            change_pct = (latest_price - prev_close) / prev_close
                    data_status["daily_start"] = df.index[0].date() if hasattr(df.index[0], "date") else None
                    data_status["daily_end"] = df.index[-1].date() if hasattr(df.index[-1], "date") else None
        except Exception:
            pass

        # ── Financial: cache-first ──
        try:
            dr = store.date_range(code, "financial")
            if dr and dr.get("rows", 0) > 0:
                data_status["has_financial"] = True
                data_status["financial_periods"] = dr["rows"]

            fin = fetcher.financial(code)
            if not fin.empty:
                latest_fin = fin.iloc[-1]
                pe = _safe_float(latest_fin.get("pe"))
                pb = _safe_float(latest_fin.get("pb"))
                dividend_yield = _safe_float(latest_fin.get("dividend_yield"))
                if not data_status["has_financial"]:
                    data_status["has_financial"] = True
                    data_status["financial_periods"] = len(fin)
        except Exception:
            pass

        items.append({
            "code": code,
            "name": name,
            "latest_price": latest_price,
            "change_pct": change_pct,
            "pe": pe,
            "pb": pb,
            "dividend_yield": dividend_yield,
            "notes": item.notes,
            "data_status": data_status,
            "data_freshness": data_freshness,
        })

    return {"id": wl.id, "name": wl.name, "items": items}


# ── Search ─────────────────────────────────────────


def search_stocks(db: Session, q: str) -> list[dict]:
    q_lower = q.strip().lower()
    if not q_lower:
        return []

    # Check DB first
    stmt = select(Stock).where(Stock.is_active == True)  # noqa: E712
    result = db.execute(stmt)
    matches = []
    for stock in result.scalars():
        if q_lower in stock.code.lower() or q_lower in (stock.name or "").lower():
            matches.append({"code": stock.code, "name": stock.name})
    if matches:
        return matches[:20]

    # Fallback to akshare
    try:
        fetcher = Fetcher()
        df = fetcher.stock_list()
        df = df.copy()
        df["code"] = df["code"].map(normalize_stock_code)
        mask = df["code"].astype(str).str.contains(q_lower) | df["name"].astype(str).str.contains(q_lower)
        hits = df[mask].head(20)
        return [{"code": normalize_stock_code(r["code"]), "name": str(r["name"])} for _, r in hits.iterrows()]
    except Exception:
        return []


# ── Export ─────────────────────────────────────────


def export_csv(db: Session, wl_id: int) -> str | None:
    wl = db.get(Watchlist, wl_id)
    if wl is None:
        return None

    output = io.StringIO()
    writer = csv_module.writer(output)
    writer.writerow(["code", "name", "notes", "added_at"])
    for item in wl.items:
        name = ""
        try:
            stock = db.get(Stock, item.code)
            if stock:
                name = stock.name
        except Exception:
            pass
        writer.writerow([item.code, name, item.notes or "", item.added_at.isoformat() if item.added_at else ""])

    return output.getvalue()


# ── Internal helpers ───────────────────────────────


def _serialize_wl(wl: Watchlist) -> dict:
    items = []
    for item in wl.items:
        name = ""
        if hasattr(item, "stock") and item.stock:
            name = item.stock.name
        items.append({
            "code": item.code,
            "name": name,
            "added_at": item.added_at,
            "notes": item.notes,
        })
    return {
        "id": wl.id,
        "name": wl.name,
        "stock_count": len(wl.items),
        "items": items,
        "created_at": wl.created_at,
    }


def _ensure_default(db: Session) -> None:
    existing = db.execute(select(Watchlist).where(Watchlist.name == DEFAULT_WL_NAME))
    if existing.scalar_one_or_none() is None:
        db.add(Watchlist(name=DEFAULT_WL_NAME))
        db.commit()


def _ensure_stock(db: Session, code: str) -> None:
    """Ensure stock exists in stocks table; create a minimal record if missing."""
    code = normalize_stock_code(code)
    if db.get(Stock, code) is not None:
        return
    name = ""
    try:
        fetcher = Fetcher()
        sl = fetcher.stock_list()
        sl = sl.copy()
        sl["code"] = sl["code"].map(normalize_stock_code)
        match = sl[sl["code"] == code]
        if not match.empty:
            name = str(match.iloc[0]["name"])
    except Exception:
        pass
    db.add(Stock(
        code=code,
        name=name or code,
        exchange="SZ" if code.startswith(("0", "3")) else "SH",
    ))
    db.flush()


def _safe_float(val) -> float | None:
    if val is None:
        return None
    try:
        v = float(val)
        return v if v == v else None  # NaN check
    except (ValueError, TypeError):
        return None

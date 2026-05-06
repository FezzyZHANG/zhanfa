"""Watchlist API endpoint tests — CRUD, items, batch ops, search, quotes, export."""


# ── Watchlist CRUD ─────────────────────────────────────

def test_list_returns_default(client):
    """GET /api/watchlists always includes at least the default group."""
    r = client.get("/api/watchlists")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert any(w["name"] == "默认" for w in data)


def test_create_watchlist(client):
    r = client.post("/api/watchlists", json={"name": "My Group"})
    assert r.status_code == 201
    wl = r.json()
    assert wl["id"] > 0
    assert wl["name"] == "My Group"
    assert wl["stock_count"] == 0
    assert wl["items"] == []
    assert "created_at" in wl


def test_create_chinese_name(client):
    r = client.post("/api/watchlists", json={"name": "沪深300成分股"})
    assert r.status_code == 201
    assert r.json()["name"] == "沪深300成分股"


def test_get_watchlist(client):
    r = client.post("/api/watchlists", json={"name": "Test"})
    wl_id = r.json()["id"]
    r = client.get(f"/api/watchlists/{wl_id}")
    assert r.status_code == 200
    assert r.json()["id"] == wl_id
    assert r.json()["name"] == "Test"


def test_get_watchlist_not_found(client):
    r = client.get("/api/watchlists/99999")
    assert r.status_code == 404


def test_update_watchlist(client):
    r = client.post("/api/watchlists", json={"name": "Old"})
    wl_id = r.json()["id"]
    r = client.put(f"/api/watchlists/{wl_id}", json={"name": "New"})
    assert r.status_code == 200
    assert r.json()["name"] == "New"


def test_delete_watchlist(client):
    r = client.post("/api/watchlists", json={"name": "ToDelete"})
    wl_id = r.json()["id"]
    r = client.delete(f"/api/watchlists/{wl_id}")
    assert r.status_code == 200
    r = client.get(f"/api/watchlists/{wl_id}")
    assert r.status_code == 404


def test_delete_default_forbidden(client):
    """Default watchlist cannot be deleted."""
    r = client.get("/api/watchlists")
    default_id = [w["id"] for w in r.json() if w["name"] == "默认"][0]
    r = client.delete(f"/api/watchlists/{default_id}")
    assert r.status_code == 400
    assert "默认" in r.json()["detail"]


# ── Items: Add ────────────────────────────────────────

def test_add_item(client):
    r = client.post("/api/watchlists", json={"name": "Test"})
    wl_id = r.json()["id"]
    r = client.post(f"/api/watchlists/{wl_id}/items", json={"code": "000001"})
    assert r.status_code == 200
    wl = r.json()
    assert wl["stock_count"] == 1
    assert any(item["code"] == "000001" for item in wl["items"])


def test_add_item_with_notes(client):
    r = client.post("/api/watchlists", json={"name": "Test"})
    wl_id = r.json()["id"]
    r = client.post(f"/api/watchlists/{wl_id}/items", json={
        "code": "000001", "notes": "重点观察"
    })
    assert r.status_code == 200
    items = r.json()["items"]
    assert items[0]["notes"] == "重点观察"


def test_add_item_duplicate_no_double_count(client):
    r = client.post("/api/watchlists", json={"name": "Test"})
    wl_id = r.json()["id"]
    client.post(f"/api/watchlists/{wl_id}/items", json={"code": "000001"})
    r = client.post(f"/api/watchlists/{wl_id}/items", json={"code": "000001"})
    assert r.status_code == 200
    wl = r.json()
    assert wl["stock_count"] == 1
    assert [i["code"] for i in wl["items"]].count("000001") == 1


def test_add_item_duplicate_updates_notes(client):
    """Re-adding the same code with new notes updates the notes."""
    r = client.post("/api/watchlists", json={"name": "Test"})
    wl_id = r.json()["id"]
    client.post(f"/api/watchlists/{wl_id}/items", json={
        "code": "000001", "notes": "old"
    })
    r = client.post(f"/api/watchlists/{wl_id}/items", json={
        "code": "000001", "notes": "new"
    })
    assert r.status_code == 200
    item = [i for i in r.json()["items"] if i["code"] == "000001"][0]
    assert item["notes"] == "new"


def test_add_item_auto_creates_stock(client):
    """Adding a code not in stocks table auto-creates a minimal record."""
    r = client.post("/api/watchlists", json={"name": "Test"})
    wl_id = r.json()["id"]
    # 002142 is unlikely to exist in test DB
    r = client.post(f"/api/watchlists/{wl_id}/items", json={"code": "002142"})
    assert r.status_code == 200
    assert any(i["code"] == "002142" for i in r.json()["items"])


# ── Items: Remove ─────────────────────────────────────

def test_remove_item(client):
    r = client.post("/api/watchlists", json={"name": "Test"})
    wl_id = r.json()["id"]
    client.post(f"/api/watchlists/{wl_id}/items", json={"code": "000001"})
    r = client.delete(f"/api/watchlists/{wl_id}/items/000001")
    assert r.status_code == 200
    r = client.get(f"/api/watchlists/{wl_id}")
    assert r.json()["stock_count"] == 0


def test_remove_item_not_found(client):
    r = client.post("/api/watchlists", json={"name": "Test"})
    wl_id = r.json()["id"]
    r = client.delete(f"/api/watchlists/{wl_id}/items/000001")
    assert r.status_code == 404


def test_remove_then_re_add(client):
    """Removing last item then re-adding should work."""
    r = client.post("/api/watchlists", json={"name": "Test"})
    wl_id = r.json()["id"]
    client.post(f"/api/watchlists/{wl_id}/items", json={"code": "000001"})
    client.delete(f"/api/watchlists/{wl_id}/items/000001")
    r = client.post(f"/api/watchlists/{wl_id}/items", json={"code": "000001"})
    assert r.status_code == 200
    assert r.json()["stock_count"] == 1


# ── Batch Operations ──────────────────────────────────

def test_batch_add_items(client):
    r = client.post("/api/watchlists", json={"name": "Test"})
    wl_id = r.json()["id"]
    r = client.post(f"/api/watchlists/{wl_id}/items/batch",
                    json={"codes": ["000001", "600519"]})
    assert r.status_code == 200
    wl = r.json()
    assert wl["stock_count"] == 2
    codes = [i["code"] for i in wl["items"]]
    assert "000001" in codes
    assert "600519" in codes


def test_batch_add_partial_duplicate(client):
    """Batch-adding codes that are already in the group skips duplicates."""
    r = client.post("/api/watchlists", json={"name": "Test"})
    wl_id = r.json()["id"]
    client.post(f"/api/watchlists/{wl_id}/items", json={"code": "000001"})
    r = client.post(f"/api/watchlists/{wl_id}/items/batch",
                    json={"codes": ["000001", "600519"]})
    assert r.status_code == 200
    assert r.json()["stock_count"] == 2


def test_batch_preview(client):
    r = client.post("/api/watchlists", json={"name": "Test"})
    wl_id = r.json()["id"]
    r = client.post(f"/api/watchlists/{wl_id}/items/batch/preview",
                    json={"codes": ["000001", "600519"]})
    assert r.status_code == 200
    data = r.json()
    assert "preview" in data
    assert "new_count" in data
    assert "existing_count" in data
    assert len(data["preview"]) == 2


def test_batch_move(client):
    r1 = client.post("/api/watchlists", json={"name": "Source"})
    r2 = client.post("/api/watchlists", json={"name": "Target"})
    src_id = r1.json()["id"]
    tgt_id = r2.json()["id"]
    client.post(f"/api/watchlists/{src_id}/items", json={"code": "000001"})

    r = client.post(f"/api/watchlists/{src_id}/items/batch-move", json={
        "target_watchlist_id": tgt_id, "codes": ["000001"]
    })
    assert r.status_code == 200
    assert r.json()["stock_count"] == 0  # source now empty


def test_batch_delete(client):
    r = client.post("/api/watchlists", json={"name": "Test"})
    wl_id = r.json()["id"]
    client.post(f"/api/watchlists/{wl_id}/items/batch",
                json={"codes": ["000001", "600519"]})

    r = client.post(f"/api/watchlists/{wl_id}/items/batch-delete",
                    json={"codes": ["000001"]})
    assert r.status_code == 200
    r = client.get(f"/api/watchlists/{wl_id}")
    assert r.json()["stock_count"] == 1
    assert r.json()["items"][0]["code"] == "600519"


# ── Search ────────────────────────────────────────────

def test_search_by_code(client):
    r = client.get("/api/watchlists/search?q=000001")
    assert r.status_code == 200
    results = r.json()
    assert isinstance(results, list)
    assert len(results) >= 1
    assert any(s["code"] == "000001" for s in results)


def test_search_by_name(client):
    r = client.get("/api/watchlists/search?q=平安")
    assert r.status_code == 200
    results = r.json()
    assert isinstance(results, list)


def test_search_empty_query(client):
    r = client.get("/api/watchlists/search?q=")
    assert r.status_code == 422  # FastAPI validates min_length=1


# ── Quotes ────────────────────────────────────────────

def test_quotes_has_fields(client):
    r = client.post("/api/watchlists", json={"name": "Test"})
    wl_id = r.json()["id"]
    client.post(f"/api/watchlists/{wl_id}/items", json={"code": "000001"})

    r = client.get(f"/api/watchlists/{wl_id}/quotes")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == wl_id
    assert "items" in data
    assert isinstance(data["items"], list)
    if data["items"]:
        item = data["items"][0]
        assert "code" in item
        assert "latest_price" in item
        assert "change_pct" in item
        assert "pe" in item
        assert "pb" in item
        assert "dividend_yield" in item
        assert "notes" in item
        assert "data_status" in item
        assert "data_freshness" in item


def test_quotes_empty_watchlist(client):
    r = client.post("/api/watchlists", json={"name": "Empty"})
    wl_id = r.json()["id"]
    r = client.get(f"/api/watchlists/{wl_id}/quotes")
    assert r.status_code == 200
    assert r.json()["items"] == []


# ── Export ────────────────────────────────────────────

def test_export_csv_content(client):
    r = client.post("/api/watchlists", json={"name": "Export"})
    wl_id = r.json()["id"]
    client.post(f"/api/watchlists/{wl_id}/items", json={"code": "000001"})

    r = client.get(f"/api/watchlists/{wl_id}/export")
    assert r.status_code == 200
    csv_text = r.text
    assert "code" in csv_text
    assert "000001" in csv_text


def test_export_empty(client):
    r = client.post("/api/watchlists", json={"name": "ExportEmpty"})
    wl_id = r.json()["id"]
    r = client.get(f"/api/watchlists/{wl_id}/export")
    assert r.status_code == 200
    assert "code" in r.text  # header row only


# ── End-to-End Lifecycle ──────────────────────────────

def test_watchlist_e2e_lifecycle(client):
    """Simulate complete user flow: create → add → quotes → notes → batch → remove → export → delete."""
    # 1. Initial: default group exists
    r = client.get("/api/watchlists")
    assert r.status_code == 200
    assert len(r.json()) >= 1

    # 2. Create a new group
    r = client.post("/api/watchlists", json={"name": "E2E Test"})
    assert r.status_code == 201
    wl_id = r.json()["id"]

    # 3. Add first stock
    r = client.post(f"/api/watchlists/{wl_id}/items",
                    json={"code": "000001", "notes": "银行股"})
    assert r.status_code == 200
    assert r.json()["stock_count"] == 1

    # 4. Add second stock
    r = client.post(f"/api/watchlists/{wl_id}/items", json={"code": "600519"})
    assert r.status_code == 200
    assert r.json()["stock_count"] == 2

    # 5. Duplicate add should not increment
    r = client.post(f"/api/watchlists/{wl_id}/items", json={"code": "000001"})
    assert r.status_code == 200
    assert r.json()["stock_count"] == 2

    # 6. Quotes return data for both stocks
    r = client.get(f"/api/watchlists/{wl_id}/quotes")
    assert r.status_code == 200
    assert len(r.json()["items"]) == 2

    # 7. Update notes
    r = client.put(f"/api/watchlists/{wl_id}/items/000001",
                   json={"notes": "重点跟踪"})
    assert r.status_code == 200
    item = [i for i in r.json()["items"] if i["code"] == "000001"][0]
    assert item["notes"] == "重点跟踪"

    # 8. Batch add more
    r = client.post(f"/api/watchlists/{wl_id}/items/batch",
                    json={"codes": ["000858", "000568"]})
    assert r.status_code == 200
    assert r.json()["stock_count"] == 4

    # 9. Batch preview
    r = client.post(f"/api/watchlists/{wl_id}/items/batch/preview",
                    json={"codes": ["000001", "999999"]})
    assert r.status_code == 200
    preview = r.json()
    assert preview["existing_count"] >= 1
    assert preview["new_count"] >= 1

    # 10. Remove one stock
    r = client.delete(f"/api/watchlists/{wl_id}/items/600519")
    assert r.status_code == 200
    r = client.get(f"/api/watchlists/{wl_id}")
    assert r.json()["stock_count"] == 3

    # 11. Export CSV
    r = client.get(f"/api/watchlists/{wl_id}/export")
    assert r.status_code == 200
    assert "000001" in r.text

    # 12. Batch delete two
    r = client.post(f"/api/watchlists/{wl_id}/items/batch-delete",
                    json={"codes": ["000858", "000568"]})
    assert r.status_code == 200
    r = client.get(f"/api/watchlists/{wl_id}")
    assert r.json()["stock_count"] == 1

    # 13. Delete the group
    r = client.delete(f"/api/watchlists/{wl_id}")
    assert r.status_code == 200
    r = client.get(f"/api/watchlists/{wl_id}")
    assert r.status_code == 404

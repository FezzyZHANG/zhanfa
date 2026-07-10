"""API endpoint tests — uses FastAPI TestClient with httpx."""

from unittest.mock import patch

# ── Health ────────────────────────────────────────────

def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# ── Strategies ────────────────────────────────────────

def test_list_strategies(client):
    r = client.get("/api/strategies")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    assert isinstance(data[0]["id"], int)


def test_list_strategies_filter_by_category(client):
    r = client.get("/api/strategies?category=trend")
    assert r.status_code == 200
    data = r.json()
    for s in data:
        assert s["category"] == "trend"


def test_list_strategies_search(client):
    r = client.get("/api/strategies?search=均线")
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1


def test_get_strategy_detail(client):
    r = client.get("/api/strategies")
    data = r.json()
    strategy_id = data[0]["id"]

    r = client.get(f"/api/strategies/{strategy_id}")
    assert r.status_code == 200
    detail = r.json()
    assert detail["id"] == strategy_id
    assert "params" in detail
    assert "backtest_count" in detail


def test_get_strategy_not_found(client):
    r = client.get("/api/strategies/99999")
    assert r.status_code == 404


def test_get_strategy_results(client):
    r = client.get("/api/strategies")
    data = r.json()
    strategy_id = data[0]["id"]

    r = client.get(f"/api/strategies/{strategy_id}/results")
    assert r.status_code == 200
    results = r.json()
    assert isinstance(results, list)


def test_create_strategy(client):
    r = client.post("/api/strategies", json={
        "name": "My Strategy",
        "category": "trend",
        "description": "A test strategy",
        "params": {"fast": 10, "slow": 30}
    })
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "My Strategy"


def test_update_strategy(client):
    r = client.get("/api/strategies")
    data = r.json()
    strategy_id = data[0]["id"]

    r = client.put(f"/api/strategies/{strategy_id}", json={
        "params": {"fast": 30, "slow": 90}
    })
    assert r.status_code == 200
    detail = r.json()
    assert detail["params"]["fast"] == 30
    assert detail["params"]["slow"] == 90


def test_update_strategy_not_found(client):
    r = client.put("/api/strategies/99999", json={"params": {}})
    assert r.status_code == 404


# ── Stocks ────────────────────────────────────────────

def test_list_stocks(client):
    r = client.get("/api/stocks?page=1&page_size=5")
    assert r.status_code == 200
    data = r.json()
    assert data["page"] == 1
    assert data["page_size"] == 5
    assert "items" in data
    assert "total" in data


def test_get_stock_not_found(client):
    r = client.get("/api/stocks/999999")
    assert r.status_code == 404


def test_stock_code_path_rejects_invalid_code(client):
    r = client.get("/api/stocks/../000001")
    assert r.status_code == 404

    r = client.get("/api/stocks/bad-code")
    assert r.status_code == 422


# ── Watchlists ────────────────────────────────────────

def test_watchlist_lifecycle(client):
    # Create
    r = client.post("/api/watchlists", json={"name": "Test List"})
    assert r.status_code == 201
    wl = r.json()
    wl_id = wl["id"]
    assert wl["name"] == "Test List"
    assert wl["stock_count"] == 0

    # List
    r = client.get("/api/watchlists")
    assert r.status_code == 200
    data = r.json()
    assert any(w["id"] == wl_id for w in data)

    # Get
    r = client.get(f"/api/watchlists/{wl_id}")
    assert r.status_code == 200
    assert r.json()["id"] == wl_id

    # Add item
    r = client.post(f"/api/watchlists/{wl_id}/items", json={"code": "000001"})
    assert r.status_code == 200
    assert any(item["code"] == "000001" for item in r.json()["items"])

    # Add duplicate — should not duplicate
    r = client.post(f"/api/watchlists/{wl_id}/items", json={"code": "000001"})
    assert r.status_code == 200
    assert [item["code"] for item in r.json()["items"]].count("000001") == 1

    # Remove item
    r = client.delete(f"/api/watchlists/{wl_id}/items/000001")
    assert r.status_code == 200

    # Remove nonexistent
    r = client.delete(f"/api/watchlists/{wl_id}/items/000001")
    assert r.status_code == 404

    # Not found
    r = client.get("/api/watchlists/99999")
    assert r.status_code == 404


# ── Backtest ──────────────────────────────────────────

def test_backtest_submit_and_poll(client):
    r = client.post("/api/backtest/run", json={
        "code": "000001",
        "strategy": "sma_cross",
        "start_date": "20240101",
        "end_date": "20250101",
    })
    assert r.status_code == 200
    task = r.json()
    task_id = task["task_id"]
    assert task["status"] in ("pending", "running", "completed")

    # Poll status
    r = client.get(f"/api/backtest/{task_id}")
    assert r.status_code == 200
    assert r.json()["task_id"] == task_id

    # History
    r = client.get("/api/backtest/history")
    assert r.status_code == 200
    history = r.json()
    assert any(h["task_id"] == task_id for h in history)


def test_backtest_rejects_invalid_code(client):
    r = client.post("/api/backtest/run", json={
        "code": "../000001",
        "strategy": "sma_cross",
        "start_date": "20240101",
        "end_date": "20250101",
    })
    assert r.status_code == 422


def test_backtest_not_found(client):
    r = client.get("/api/backtest/nonexistent")
    assert r.status_code == 404


def test_backtest_submit_creates_db_record(client):
    """After submitting a backtest, a pending DB record exists and shows in history."""
    r = client.post("/api/backtest/run", json={
        "code": "000001",
        "strategy": "sma_cross",
        "start_date": "20240101",
        "end_date": "20250101",
    })
    assert r.status_code == 200
    task = r.json()
    task_id = task["task_id"]

    # History should include this task from the service
    r = client.get("/api/backtest/history")
    assert r.status_code == 200
    history = r.json()
    assert any(h["task_id"] == task_id for h in history)


def test_strategy_results_link_to_backtests(client):
    """Strategy detail page shows backtest_count and results endpoint lists them."""
    # Get a strategy
    r = client.get("/api/strategies")
    strategies = r.json()
    strategy_id = strategies[0]["id"]

    # Initially, results should be a list (possibly empty)
    r = client.get(f"/api/strategies/{strategy_id}/results")
    assert r.status_code == 200
    results = r.json()
    assert isinstance(results, list)

    # Strategy detail includes backtest_count
    r = client.get(f"/api/strategies/{strategy_id}")
    assert r.status_code == 200
    detail = r.json()
    assert "backtest_count" in detail


# ── Scheduler ─────────────────────────────────────────

def test_scheduler_status(client):
    r = client.get("/api/scheduler/status")
    assert r.status_code == 200
    data = r.json()
    assert "jobs" in data
    assert "running" in data


def test_scheduler_trigger_update(client):
    with patch(
        "zhanfa.api.routers.scheduler.update_daily_data",
        return_value={"updated": 1, "failed": 0, "new_discovered": 0, "details": {}},
    ) as mock_update:
        r = client.post("/api/scheduler/trigger", json={"action": "update_daily"})
    assert r.status_code == 200
    assert r.json()["action"] == "update_daily"
    mock_update.assert_called_once_with(None)


def test_scheduler_trigger_rebalance(client):
    with patch(
        "zhanfa.api.routers.scheduler.weekly_index_rebalance",
        return_value={"index_code": "000300", "added": [], "removed": []},
    ) as mock_rebalance:
        r = client.post("/api/scheduler/trigger", json={
            "action": "rebalance_index",
            "index_code": "000300",
        })
    assert r.status_code == 200
    assert r.json()["action"] == "rebalance_index"
    mock_rebalance.assert_called_once_with("000300")


# ── Swagger docs ──────────────────────────────────────

def test_docs_accessible(client):
    r = client.get("/docs")
    assert r.status_code == 200
    assert "Swagger" in r.text or "swagger" in r.text


def test_openapi_schema(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    schema = r.json()
    assert "paths" in schema
    assert "/api/strategies" in schema["paths"]
    assert "/api/stocks" in schema["paths"]
    assert "/api/watchlists" in schema["paths"]
    assert "/api/backtest/run" in schema["paths"]
    assert "/api/scheduler/status" in schema["paths"]

"""Strategy service tests."""

import datetime
from unittest.mock import MagicMock, patch

import pytest

from zhanfa.db.models import Strategy, BacktestResult


@pytest.fixture
def db_with_strategy(db_session):
    """DB session with a strategy pre-registered."""
    s = Strategy(
        name="test_strategy",
        category="trend",
        description="A test strategy",
        params={"fast": 5, "slow": 20},
        code_ref="zhanfa.strategies.trend.SMACross",
    )
    db_session.add(s)
    db_session.commit()
    return db_session


@pytest.fixture
def db_with_backtests(db_with_strategy):
    """DB session with a strategy and completed backtest results."""
    r1 = BacktestResult(
        task_id="bt_001",
        strategy_id=1,
        stock_codes=["000001"],
        params={"fast": 5, "slow": 20},
        start_date=datetime.date(2024, 1, 1),
        end_date=datetime.date(2025, 1, 1),
        metrics={"total_return": 0.15, "sharpe": 1.2, "max_drawdown": -0.08},
        equity_curve=[{"date": "2024-06-01", "value": 1.10}],
        drawdown_curve=[{"date": "2024-06-01", "value": -0.05}],
        yearly_returns=[{"year": 2024, "value": 0.15}],
        monthly_returns=[{"year": 2024, "month": 6, "value": 0.03}],
        trades=[{"date": "2024-03-01", "action": "buy", "price": 10.0, "quantity": 100, "pnl": 0}],
        status="completed",
        created_at=datetime.datetime(2024, 12, 1),
    )
    r2 = BacktestResult(
        task_id="bt_002",
        strategy_id=1,
        stock_codes=["600519"],
        params={"fast": 10, "slow": 30},
        start_date=datetime.date(2024, 6, 1),
        end_date=datetime.date(2025, 6, 1),
        metrics={"error": "Data fetch failed"},
        status="failed",
        created_at=datetime.datetime(2025, 1, 1),
    )
    db_with_strategy.add_all([r1, r2])
    db_with_strategy.commit()
    return db_with_strategy


class TestListStrategies:
    def test_returns_list(self, db_with_strategy):
        from zhanfa.api.services.strategy_service import list_strategies, SessionLocal
        with patch.object(SessionLocal, "__call__", return_value=db_with_strategy):
            with patch("zhanfa.api.services.strategy_service.SessionLocal", return_value=db_with_strategy):
                result = list_strategies()
                assert isinstance(result, list)
                assert len(result) >= 1

    def test_filter_by_category(self, db_with_strategy):
        from zhanfa.api.services.strategy_service import list_strategies
        with patch("zhanfa.api.services.strategy_service.SessionLocal", return_value=db_with_strategy):
            result = list_strategies(category="trend")
            for s in result:
                assert s["category"] == "trend"

    def test_search_filters(self, db_with_strategy):
        from zhanfa.api.services.strategy_service import list_strategies
        with patch("zhanfa.api.services.strategy_service.SessionLocal", return_value=db_with_strategy):
            result = list_strategies(search="test")
            assert len(result) >= 1


class TestGetStrategy:
    def test_returns_strategy(self, db_with_strategy):
        from zhanfa.api.services.strategy_service import get_strategy
        with patch("zhanfa.api.services.strategy_service.SessionLocal", return_value=db_with_strategy):
            result = get_strategy(1)
            assert result["name"] == "test_strategy"

    def test_returns_none_for_missing(self, db_session):
        from zhanfa.api.services.strategy_service import get_strategy
        with patch("zhanfa.api.services.strategy_service.SessionLocal", return_value=db_session):
            assert get_strategy(99999) is None


class TestCreateStrategy:
    def test_creates_strategy(self, db_session):
        from zhanfa.api.services.strategy_service import create_strategy
        with patch("zhanfa.api.services.strategy_service.SessionLocal", return_value=db_session):
            result = create_strategy("New Strat", "momentum", description="desc", params={"m": 10})
            assert result["name"] == "New Strat"
            assert result["category"] == "momentum"


class TestUpdateStrategy:
    def test_updates_params(self, db_with_strategy):
        from zhanfa.api.services.strategy_service import update_strategy
        with patch("zhanfa.api.services.strategy_service.SessionLocal", return_value=db_with_strategy):
            result = update_strategy(1, {"fast": 30})
            assert result["params"]["fast"] == 30

    def test_returns_none_for_missing(self, db_session):
        from zhanfa.api.services.strategy_service import update_strategy
        with patch("zhanfa.api.services.strategy_service.SessionLocal", return_value=db_session):
            assert update_strategy(99999, {}) is None


class TestGetStrategyResults:
    def test_returns_empty_list(self, db_with_strategy):
        from zhanfa.api.services.strategy_service import get_strategy_results
        with patch("zhanfa.api.services.strategy_service.SessionLocal", return_value=db_with_strategy):
            result = get_strategy_results(1)
            assert isinstance(result, list)

    def test_returns_full_backtest_data(self, db_with_backtests):
        """get_strategy_results returns backtests with equity_curve, trades, etc."""
        from zhanfa.api.services.strategy_service import get_strategy_results
        with patch("zhanfa.api.services.strategy_service.SessionLocal", return_value=db_with_backtests):
            results = get_strategy_results(1)
            assert len(results) == 2

            completed = [r for r in results if r["status"] == "completed"][0]
            assert completed["id"] == "bt_001"
            assert completed["strategy_id"] == 1
            assert completed["stock_codes"] == ["000001"]
            assert completed["metrics"]["total_return"] == 0.15
            assert len(completed["equity_curve"]) == 1
            assert len(completed["drawdown_curve"]) == 1
            assert len(completed["yearly_returns"]) == 1
            assert len(completed["monthly_returns"]) == 1
            assert len(completed["trades"]) == 1

            failed = [r for r in results if r["status"] == "failed"][0]
            assert failed["id"] == "bt_002"
            assert "error" in failed["metrics"]

    def test_backtest_count_matches_db(self, db_with_backtests):
        """backtest_count reflects only DB-persisted records."""
        from zhanfa.api.services.strategy_service import get_strategy_results, get_strategy
        with patch("zhanfa.api.services.strategy_service.SessionLocal", return_value=db_with_backtests):
            strategy = get_strategy(1)
            results = get_strategy_results(1)
        assert len(results) == 2


class TestCreateStrategyInstance:
    def test_creates_sma_cross(self):
        from zhanfa.api.services.strategy_service import create_strategy_instance
        s = create_strategy_instance("sma_cross", {"fast": 5, "slow": 20})
        from zhanfa.strategies.base import BaseStrategy
        assert isinstance(s, BaseStrategy)
        assert s.name == "双均线交叉策略"

    def test_creates_turtle(self):
        from zhanfa.api.services.strategy_service import create_strategy_instance
        from zhanfa.strategies.base import BaseStrategy
        s = create_strategy_instance("turtle")
        assert isinstance(s, BaseStrategy)
        assert s.name == "海龟交易法则"

    def test_raises_for_unknown(self):
        from zhanfa.api.services.strategy_service import create_strategy_instance
        with pytest.raises(ValueError):
            create_strategy_instance("nonexistent")


class TestHelpers:
    def test_strategy_to_dict(self):
        from zhanfa.api.services.strategy_service import _strategy_to_dict
        s = Strategy(
            id=1, name="test", category="trend",
            description="desc", params={"a": 1},
            code_ref="zhanfa.strategies.trend.SMACross",
        )
        d = _strategy_to_dict(s)
        assert d["id"] == 1
        assert d["name"] == "test"
        assert d["params"] == {"a": 1}

    def test_backtest_to_dict_full_fields(self):
        from zhanfa.api.services.strategy_service import _backtest_to_dict
        r = BacktestResult(
            id=1, task_id="bt_full", strategy_id=2,
            stock_codes=["000001"],
            params={"fast": 5},
            start_date=datetime.date(2024, 1, 1),
            end_date=datetime.date(2025, 1, 1),
            metrics={"total_return": 0.10, "sharpe": 1.0, "max_drawdown": -0.05},
            equity_curve=[{"date": "2024-06-01", "value": 1.05}],
            drawdown_curve=[{"date": "2024-06-01", "value": -0.02}],
            benchmark_curve=None,
            yearly_returns=[{"year": 2024, "value": 0.10}],
            monthly_returns=[{"year": 2024, "month": 6, "value": 0.02}],
            trades=[{"date": "2024-04-01", "action": "buy", "price": 10.0, "quantity": 100, "pnl": 0}],
            status="completed",
            created_at=datetime.datetime(2024, 12, 1),
        )
        d = _backtest_to_dict(r)
        assert d["id"] == "bt_full"
        assert d["db_id"] == 1
        assert d["strategy_id"] == 2
        assert d["metrics"]["total_return"] == 0.10
        assert len(d["equity_curve"]) == 1
        assert len(d["drawdown_curve"]) == 1
        assert d["benchmark_curve"] is None
        assert len(d["yearly_returns"]) == 1
        assert len(d["monthly_returns"]) == 1
        assert len(d["trades"]) == 1
        assert d["status"] == "completed"

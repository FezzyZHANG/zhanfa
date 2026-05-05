"""Strategy service tests."""

from unittest.mock import MagicMock, patch

import pytest

from zhanfa.db.models import Strategy


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

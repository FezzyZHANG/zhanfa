"""Strategy registration tests."""

from unittest.mock import MagicMock, patch

import pytest

from zhanfa.db.models import Strategy
from zhanfa.strategies.base import BaseStrategy


class StubStrategy(BaseStrategy):
    """Test strategy stub.

    Parameters:
        fast: 快线周期 (默认 10)
        slow: 慢线周期 (默认 30)
    """
    name = "stub"

    def __init__(self, fast: int = 10, slow: int = 30):
        self.fast = fast
        self.slow = slow

    def generate_signals(self, data):
        import pandas as pd
        return pd.Series(True, index=data.index)


class TestExtractParamsFromCls:
    def test_extracts_params(self):
        from zhanfa.db.register_strategies import _extract_params_from_cls
        params = _extract_params_from_cls(StubStrategy)
        assert "fast" in params
        assert params["fast"]["type"] == "int"
        assert params["fast"]["default"] == 10
        assert "slow" in params
        assert params["slow"]["type"] == "int"
        assert params["slow"]["default"] == 30

    def test_extracts_descriptions(self):
        from zhanfa.db.register_strategies import _extract_params_from_cls
        params = _extract_params_from_cls(StubStrategy)
        assert params["fast"]["description"] == "快线周期 (默认 10)"


class TestAnnotationToStr:
    def test_converts_types(self):
        from zhanfa.db.register_strategies import _annotation_to_str
        assert _annotation_to_str(int) == "int"
        assert _annotation_to_str(float) == "float"
        assert _annotation_to_str(str) == "str"
        assert _annotation_to_str(bool) == "bool"
        assert _annotation_to_str(None) == "any"

    def test_unknown_type(self):
        from zhanfa.db.register_strategies import _annotation_to_str
        result = _annotation_to_str(list)
        assert "list" in result.lower()


class TestExtractParamDesc:
    def test_extracts_from_docstring(self):
        from zhanfa.db.register_strategies import _extract_param_desc
        desc = _extract_param_desc(StubStrategy.__doc__ or "", "fast")
        assert "快线周期" in desc

    def test_returns_empty_for_missing(self):
        from zhanfa.db.register_strategies import _extract_param_desc
        assert _extract_param_desc("", "nonexistent") == ""


class TestRegisterModule:
    def test_registers_class(self, db_session):
        from zhanfa.db.register_strategies import _register_module

        mock_mod = MagicMock()
        mock_mod.__name__ = "zhanfa.strategies.trend.stub"
        registered = []

        from unittest.mock import patch as mock_patch
        with mock_patch("zhanfa.db.register_strategies.inspect.getmembers", return_value=[
            ("StubStrategy", StubStrategy),
        ]):
            _register_module(mock_mod, db_session, registered)

        assert len(registered) >= 1
        # Verify it was upserted to DB
        row = db_session.query(Strategy).filter_by(code_ref=registered[0]).first()
        assert row is not None
        assert row.name == "stub"


class TestRegisterStrategy:
    def test_creates_new(self, db_session):
        from zhanfa.db.register_strategies import _register_strategy
        # Patch module path so category inference finds "trend"
        orig_module = StubStrategy.__module__
        StubStrategy.__module__ = "zhanfa.strategies.trend.stub"
        try:
            _register_strategy(StubStrategy, db_session)
            row = db_session.query(Strategy).filter_by(name="stub").first()
            assert row is not None
            assert row.category == "trend"
        finally:
            StubStrategy.__module__ = orig_module

    def test_updates_existing(self, db_session):
        from zhanfa.db.register_strategies import _register_strategy

        # First registration
        _register_strategy(StubStrategy, db_session)

        # Modify and re-register
        class ModifiedStub(StubStrategy):
            name = "stub_modified"

        _register_strategy(ModifiedStub, db_session)

        row = db_session.query(Strategy).filter_by(code_ref=ModifiedStub.__module__ + ".ModifiedStub").first()
        assert row is not None

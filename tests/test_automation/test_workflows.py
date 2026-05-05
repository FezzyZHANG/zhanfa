"""Workflow automation tests."""

from unittest.mock import MagicMock, patch

import pandas as pd


class TestUpdateDailyData:
    def test_updates_given_codes(self):
        from zhanfa.automation.workflows import update_daily_data

        mock_fetcher = MagicMock()
        mock_fetcher.daily.return_value = pd.DataFrame({"close": [10.0, 11.0]})
        mock_fetcher.stock_list.return_value = pd.DataFrame({"code": ["000001"], "name": ["test"]})

        with patch("zhanfa.automation.workflows.Fetcher", return_value=mock_fetcher):
            result = update_daily_data(codes=["000001", "600519"])

        assert result["updated"] == 2
        assert result["failed"] == 0
        assert result["details"]["000001"] == 2

    def test_handles_error_per_code(self):
        from zhanfa.automation.workflows import update_daily_data

        mock_fetcher = MagicMock()
        mock_fetcher.stock_list.return_value = pd.DataFrame({"code": ["000001"], "name": ["test"]})

        def side_effect(code):
            if code == "bad_code":
                raise RuntimeError("fail")
            return pd.DataFrame({"close": [1.0]})

        mock_fetcher.daily.side_effect = side_effect

        with patch("zhanfa.automation.workflows.Fetcher", return_value=mock_fetcher):
            result = update_daily_data(codes=["000001", "bad_code"])

        assert result["updated"] == 1
        assert result["failed"] == 1
        assert result["details"]["000001"] == 1
        assert result["details"]["bad_code"] == -1

    def test_discover_new_stocks(self):
        from zhanfa.automation.workflows import update_daily_data

        mock_fetcher = MagicMock()
        mock_fetcher.daily.return_value = pd.DataFrame({"close": [10.0]})
        mock_fetcher.stock_list.return_value = pd.DataFrame({
            "code": ["000001", "000002", "600519"],
            "name": ["平安银行", "万科A", "贵州茅台"],
        })

        # Store returns only one cached code, two others should be discovered
        with patch("zhanfa.automation.workflows.Store") as MockStore:
            mock_store_instance = MockStore.return_value
            mock_store_instance.codes.return_value = ["000001"]

            with patch("zhanfa.automation.workflows.Fetcher", return_value=mock_fetcher):
                result = update_daily_data(discover_new=True)

        assert result["new_discovered"] == 2
        assert result["stock_imported"] == 3
        assert result["updated"] >= 1

    def test_discover_new_disabled(self):
        from zhanfa.automation.workflows import update_daily_data

        mock_fetcher = MagicMock()
        mock_fetcher.daily.return_value = pd.DataFrame({"close": [10.0]})

        with patch("zhanfa.automation.workflows.Store") as MockStore:
            mock_store_instance = MockStore.return_value
            mock_store_instance.codes.return_value = ["000001"]

            with patch("zhanfa.automation.workflows.Fetcher", return_value=mock_fetcher):
                result = update_daily_data(discover_new=False)

        assert result["new_discovered"] == 0


class TestWeeklyIndexRebalance:
    def test_returns_structured_result(self):
        from zhanfa.automation.workflows import weekly_index_rebalance

        mock_fetcher = MagicMock()
        mock_fetcher.index_components.return_value = ["000001", "600519", "000858"]

        with patch("zhanfa.automation.workflows.Fetcher", return_value=mock_fetcher), \
             patch("zhanfa.automation.workflows.Store") as MockStore:
            mock_store = MockStore.return_value
            mock_store.load.return_value = None  # No previous data

            result = weekly_index_rebalance("000300")

        assert result["index_code"] == "000300"
        assert result["current_count"] == 3
        assert result["previous_count"] == 0
        assert set(result["added"]) == {"000001", "000858", "600519"}  # All new
        assert result["removed"] == []
        assert "000001" in result["current"]

    def test_detects_additions_and_removals(self):
        from zhanfa.automation.workflows import weekly_index_rebalance

        mock_fetcher = MagicMock()
        mock_fetcher.index_components.return_value = ["000001", "600519", "000858"]

        with patch("zhanfa.automation.workflows.Fetcher", return_value=mock_fetcher), \
             patch("zhanfa.automation.workflows.Store") as MockStore:
            mock_store = MockStore.return_value
            # Previous had 000001, 000002, 600519
            mock_store.load.return_value = pd.DataFrame({
                "code": ["000001", "000002", "600519"],
            })

            result = weekly_index_rebalance("000300")

        assert result["current_count"] == 3
        assert result["previous_count"] == 3
        assert result["added"] == ["000858"]    # New in current
        assert result["removed"] == ["000002"]   # Gone from previous

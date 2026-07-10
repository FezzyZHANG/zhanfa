"""Backtest report tests."""

from __future__ import annotations

from unittest.mock import patch

import pandas as pd

from zhanfa.backtest.report import generate_report, save_report


class FakePortfolio:
    def value(self) -> pd.Series:
        return pd.Series([100000.0, 101000.0], index=pd.date_range("2024-01-01", periods=2))

    def stats(self) -> dict:
        return {
            "Total Trades": 3,
            "Win Rate [%]": 66.67,
            "Sharpe Ratio": 1.23,
            "Max Drawdown [%]": 4.56,
        }


def _metrics() -> dict:
    return {
        "total_return": 0.1,
        "ann_return": 0.2,
        "ann_volatility": 0.3,
        "sharpe": 1.2,
        "sortino": 1.4,
        "max_drawdown": -0.05,
        "calmar": 4.0,
        "win_rate": 0.6,
        "years": 1.0,
    }


def test_generate_report_without_benchmark_formats_sections():
    with patch("zhanfa.backtest.report.compute_metrics", return_value=_metrics()):
        report = generate_report(FakePortfolio())

    assert "# 回测报告" in report
    assert "| 总收益率 | 10.00% |" in report
    assert "| 总交易次数 | 3 |" in report
    assert "## 超额收益" not in report


def test_generate_report_with_benchmark_adds_excess_section():
    metrics = {**_metrics(), "excess_return": 0.03, "ann_excess": 0.05}

    with patch("zhanfa.backtest.report.compute_metrics", return_value=metrics):
        report = generate_report(FakePortfolio(), benchmark=pd.Series([1.0, 1.1]))

    assert "## 超额收益" in report
    assert "| 超额收益 | 3.00% |" in report


def test_save_report_writes_markdown(tmp_path):
    path = tmp_path / "report.md"

    with patch("zhanfa.backtest.report.compute_metrics", return_value=_metrics()):
        save_report(FakePortfolio(), str(path))

    assert path.read_text(encoding="utf-8").startswith("# 回测报告")

"""回测层 - vectorbt 封装"""

from zhanfa.backtest.engine import run_backtest, run_portfolio_backtest, compare_strategies
from zhanfa.backtest.metrics import compute_metrics
from zhanfa.backtest.report import generate_report

__all__ = [
    "run_backtest",
    "run_portfolio_backtest",
    "compare_strategies",
    "compute_metrics",
    "generate_report",
]

"""回测报告生成"""

import pandas as pd
import vectorbt as vbt

from zhanfa.backtest.metrics import compute_metrics


def generate_report(pf: vbt.Portfolio, benchmark: pd.Series | None = None) -> str:
    """生成 Markdown 格式回测报告。

    Args:
        pf: vectorbt Portfolio 对象
        benchmark: 基准收盘价序列（可选）

    Returns:
        Markdown 字符串
    """
    equity = pf.value()
    metrics = compute_metrics(equity, benchmark)

    lines = [
        "# 回测报告",
        "",
        "## 绩效指标",
        "",
        "| 指标 | 数值 |",
        "|------|------|",
        f"| 总收益率 | {metrics.get('total_return', 0):.2%} |",
        f"| 年化收益率 | {metrics.get('ann_return', 0):.2%} |",
        f"| 年化波动率 | {metrics.get('ann_volatility', 0):.2%} |",
        f"| 夏普比率 | {metrics.get('sharpe', 0):.2f} |",
        f"| 索提诺比率 | {metrics.get('sortino', 0):.2f} |",
        f"| 最大回撤 | {metrics.get('max_drawdown', 0):.2%} |",
        f"| 卡玛比率 | {metrics.get('calmar', 0):.2f} |",
        f"| 胜率 | {metrics.get('win_rate', 0):.2%} |",
        f"| 回测年数 | {metrics.get('years', 0):.1f} 年 |",
    ]

    if "excess_return" in metrics:
        lines.extend([
            "",
            "## 超额收益",
            "",
            f"| 超额收益 | {metrics['excess_return']:.2%} |",
            f"| 年化超额 | {metrics['ann_excess']:.2%} |",
        ])

    stats = pf.stats()
    lines.extend([
        "",
        "## 交易统计",
        "",
        f"| 总交易次数 | {stats.get('Total Trades', 0)} |",
        f"| 胜率 | {stats.get('Win Rate [%]', 0):.2f}% |",
        f"| 夏普比率 | {stats.get('Sharpe Ratio', 0):.2f} |",
        f"| 最大回撤 | {stats.get('Max Drawdown [%]', 0):.2f}% |",
    ])

    return "\n".join(lines)


def save_report(pf: vbt.Portfolio, filepath: str, benchmark: pd.Series | None = None) -> None:
    """生成报告并保存到文件"""
    report = generate_report(pf, benchmark)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report)

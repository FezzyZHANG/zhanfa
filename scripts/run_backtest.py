"""运行双均线策略回测并输出报告"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from zhanfa.data.fetcher import Fetcher
from zhanfa.data.pipeline import Pipeline
from zhanfa.strategies.trend.sma_cross import SMACross
from zhanfa.backtest.engine import run_backtest_from_strategy
from zhanfa.backtest.report import generate_report


def main():
    code = "000300"  # 默认
    if len(sys.argv) > 1:
        code = sys.argv[1]

    print(f"获取 {code} 指数数据...")
    fetcher = Fetcher()
    df = fetcher.index_daily(code)

    print("清洗数据...")
    df = Pipeline.clean(df)

    print("运行双均线策略...")
    strategy = SMACross(fast=20, slow=60)
    pf = run_backtest_from_strategy(df, strategy)

    print("\n" + generate_report(pf))


if __name__ == "__main__":
    main()

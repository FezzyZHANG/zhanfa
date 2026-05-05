"""
全市场分钟级数据批量拉取脚本

用法:
  python scripts/fetch_minute.py --freq 60       # 1h 数据
  python scripts/fetch_minute.py --freq 15       # 15min 数据
  python scripts/fetch_minute.py --freq 30       # 30min 数据
  python scripts/fetch_minute.py --all           # 全部频率
  python scripts/fetch_minute.py --freq 60 --max 50        # 仅拉 50 只
  python scripts/fetch_minute.py --freq 60 --force         # 强制覆写
  python scripts/fetch_minute.py --freq 60 --codes 000001,600519  # 指定股票
"""

import argparse
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from zhanfa.data.fetcher import Fetcher
from zhanfa.data.store import Store

LOG_DIR = Path(__file__).parent


def setup_log(freq: str) -> Path:
    """返回错误日志文件路径，确保目录存在"""
    import getpass
    username = getpass.getuser()
    date_str = datetime.now().strftime("%Y%m%d")
    log_path = LOG_DIR / f"fetch_minute_{freq}_{username}_{date_str}.log"
    return log_path


def write_errors(log_path: Path, errors: list[tuple[str, str]]) -> None:
    """将错误列表写入日志文件"""
    if not errors:
        return
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"fetch_minute errors — {datetime.now()}\n")
        f.write(f"{'=' * 50}\n")
        for code, msg in errors:
            f.write(f"  {code}: {msg}\n")
        f.write(f"\nTotal errors: {len(errors)}\n")


def fetch_frequency(fetcher: Fetcher, store: Store, codes: list[str], period: str,
                    force: bool, log_path: Path) -> dict:
    """拉取指定频率的分钟数据，返回统计信息"""
    freq = f"minute_{period}"
    errors: list[tuple[str, str]] = []
    success = 0
    skipped = 0
    failed = 0

    n = len(codes)
    t_start = time.time()

    for i, code in enumerate(codes):
        # 断点续传：已缓存且非强制则跳过
        if store.exists(code, freq) and not force:
            skipped += 1
            if (i + 1) % 200 == 0:
                print(f"  [{i+1:4d}/{n}] {code} ... skipped (cached)",
                      flush=True)
            continue

        try:
            df = fetcher.minute(code, period=period)
            success += 1
            if (i + 1) % 50 == 0 or success <= 3:
                date_info = ""
                if len(df) > 0:
                    date_info = f", {df.index[0]} ~ {df.index[-1]}"
                print(f"  [{i+1:4d}/{n}] {code}: {len(df)} 行{date_info}",
                      flush=True)
        except Exception as e:
            failed += 1
            errors.append((code, str(e)[:200]))
            if failed <= 5:
                print(f"  [{i+1:4d}/{n}] {code}: FAIL — {e}", flush=True)
            time.sleep(1)  # 出错后多等一会儿

    elapsed = time.time() - t_start
    result = {
        "freq": freq,
        "period": period,
        "total": n,
        "success": success,
        "skipped": skipped,
        "failed": failed,
        "elapsed_sec": elapsed,
    }

    # 写入错误日志
    write_errors(log_path, errors)

    return result


def print_summary(results: list[dict]) -> None:
    """打印汇总统计"""
    print("\n" + "=" * 60)
    print("汇总")
    print("=" * 60)
    for r in results:
        freq_label = r["freq"]
        m, s = divmod(int(r["elapsed_sec"]), 60)
        print(f"  {freq_label}: {r['success']} 成功, "
              f"{r['skipped']} 跳过, {r['failed']} 失败, "
              f"耗时 {m}m{s:02d}s")


def main():
    parser = argparse.ArgumentParser(
        description="全市场分钟级数据批量拉取",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  fetch_minute.py --freq 60 --max 50     # 拉取 50 只 1h 数据
  fetch_minute.py --all --max 100        # 全部频率，各 100 只
  fetch_minute.py --freq 15 --force      # 强制覆写 15min 数据
  fetch_minute.py --freq 60 --codes 000001,600519  # 指定股票
        """,
    )
    parser.add_argument("--freq", choices=["15", "30", "60"],
                        help="频率: 15=15min, 30=30min, 60=60min(1h)")
    parser.add_argument("--all", action="store_true",
                        help="拉取全部频率 (15/30/60)")
    parser.add_argument("--codes", type=str,
                        help="指定股票代码，逗号分隔 (如 000001,600519)")
    parser.add_argument("--max", type=int, default=0,
                        help="限制拉取数量 (0=全部)")
    parser.add_argument("--force", action="store_true",
                        help="强制覆写已缓存数据")
    parser.add_argument("--source", choices=["sina", "em"], default="sina",
                        help="数据源: sina (默认) 或 em (东方财富)")

    args = parser.parse_args()

    if not args.freq and not args.all:
        parser.error("必须指定 --freq 或 --all")
    if args.freq and args.all:
        parser.error("--freq 和 --all 不能同时使用")

    periods = ["15", "30", "60"] if args.all else [args.freq]
    period_labels = {"15": "15min", "30": "30min", "60": "1h"}
    print(f"分钟数据批量拉取 — 频率: {', '.join(period_labels[p] for p in periods)}")
    print(f"数据源: {args.source}, force={args.force}, max={args.max or '全部'}")
    print()

    fetcher = Fetcher()
    store = Store()

    # 获取股票列表
    if args.codes:
        codes = [c.strip() for c in args.codes.split(",") if c.strip()]
        print(f"指定股票: {len(codes)} 只")
    else:
        print("获取全A股列表...")
        stock_df = fetcher.stock_list()
        codes = sorted(stock_df["code"].tolist())
        print(f"共 {len(codes)} 只")

    if args.max and args.max < len(codes):
        codes = codes[:args.max]
        print(f"限制拉取: {len(codes)} 只")

    results = []
    for period in periods:
        label = period_labels[period]
        print(f"\n{'—' * 40}")
        print(f"开始拉取 {label} (period={period})")
        print(f"{'—' * 40}")

        log_path = setup_log(period)
        result = fetch_frequency(fetcher, store, codes, period, args.force, log_path)
        results.append(result)

    print_summary(results)

    # 提示错误日志位置
    for r in results:
        if r["failed"] > 0:
            period_str = r["period"]
            print(f"\n错误详情: {LOG_DIR}/fetch_minute_{period_str}_*.log")


if __name__ == "__main__":
    main()

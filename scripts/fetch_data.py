"""拉取沪深300成分股日线数据并缓存"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from zhanfa.data.fetcher import Fetcher
from zhanfa.data.store import Store


def main():
    fetcher = Fetcher()
    store = Store()

    print("获取沪深300成分股列表...")
    codes = fetcher.index_components("000300")
    print(f"共 {len(codes)} 只")

    print("批量获取日线数据（已缓存的会跳过）...")
    for i, code in enumerate(codes[:5]):  # 先取前5只示例
        print(f"  [{i+1}/{min(len(codes), 5)}] {code}...", end=" ")
        try:
            df = fetcher.daily(code)
            print(f"{len(df)} 行, {df.index[0].date()} ~ {df.index[-1].date()}")
        except Exception as e:
            print(f"失败: {e}")

    cached = store.codes("daily")
    print(f"\n缓存中共有 {len(cached)} 只股票的日线数据")
    if cached:
        print(f"示例: {cached[:5]}")


if __name__ == "__main__":
    main()

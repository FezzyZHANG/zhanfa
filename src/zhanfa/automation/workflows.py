"""自动化工作流编排"""

import logging

import pandas as pd

from zhanfa.data.fetcher import Fetcher
from zhanfa.data.store import Store
from zhanfa.db.import_data import import_stocks_from_frame, normalize_stock_code

logger = logging.getLogger(__name__)


def update_daily_data(
    codes: list[str] | None = None,
    discover_new: bool = True,
    max_new: int = 50,
) -> dict:
    """每日数据更新：拉取最新日线并缓存，可选发现新上市股票。

    Args:
        codes: 要更新的股票代码列表，None 则从已有缓存推断。
        discover_new: 是否从全市场列表中自动发现未缓存的新股票。
        max_new: 每次最多新增的股票数（避免首次运行拉取全市场）。

    Returns:
        {"updated": int, "failed": int, "new_discovered": int, "details": {...}}
    """
    fetcher = Fetcher()
    store = Store()

    if codes is None:
        codes = store.codes("daily")

    # 新股票发现
    new_codes: list[str] = []
    stock_imported = 0
    if discover_new:
        try:
            all_stocks = fetcher.stock_list()
            stock_imported = import_stocks_from_frame(all_stocks)
            cached_set = set(store.codes("daily"))
            new_codes = [
                normalize_stock_code(c)
                for c in all_stocks["code"].tolist()
                if normalize_stock_code(c) not in cached_set
            ]
            if len(new_codes) > max_new:
                new_codes = new_codes[:max_new]
            logger.info(f"发现 {len(new_codes)} 只未缓存股票，将新增拉取")
        except Exception as e:
            logger.warning(f"新股票发现失败: {e}")

    all_codes = list(dict.fromkeys([normalize_stock_code(c) for c in codes] + new_codes))  # 去重保序

    updated = 0
    failed = 0
    details: dict[str, int] = {}

    for code in all_codes:
        try:
            df = fetcher.daily(code)
            details[code] = len(df)
            updated += 1
        except Exception as e:
            logger.error(f"更新 {code} 失败: {e}")
            details[code] = -1
            failed += 1

    return {
        "updated": updated,
        "failed": failed,
        "new_discovered": len(new_codes),
        "stock_imported": stock_imported,
        "details": details,
    }


def update_minute_data(codes: list[str], period: str) -> dict:
    """分钟级数据刷新：为指定股票拉取分钟线并缓存。

    Args:
        codes: 股票代码列表。
        period: "15" | "30" | "60"

    Returns:
        {"updated": int, "failed": int, "new_discovered": 0, "details": {...}}
    """
    fetcher = Fetcher()

    updated = 0
    failed = 0
    details: dict[str, int] = {}

    for code in codes:
        try:
            df = fetcher.minute(code, period=period)
            details[code] = len(df)
            updated += 1
        except Exception as e:
            logger.error(f"更新分钟 {code} (period={period}) 失败: {e}")
            details[code] = -1
            failed += 1

    return {
        "updated": updated,
        "failed": failed,
        "new_discovered": 0,
        "details": details,
    }


def weekly_index_rebalance(index_code: str = "000300") -> dict:
    """每周指数调仓：对比新旧成分股，记录变更并更新缓存。

    Args:
        index_code: 指数代码，默认沪深300。

    Returns:
        {
            "index_code": str,
            "current_count": int,
            "previous_count": int,
            "added": list[str],
            "removed": list[str],
        }
    """
    fetcher = Fetcher()
    store = Store()
    prev_cache_key = f"rebalance_{index_code}_prev"

    # 获取新成分股
    current = fetcher.index_components(index_code)

    # 加载上一期缓存
    previous_df = store.load(prev_cache_key, "meta")
    previous: list[str] = previous_df["code"].tolist() if previous_df is not None else []

    # 对比差异
    cur_set = set(current)
    prev_set = set(previous)
    added = sorted(cur_set - prev_set)
    removed = sorted(prev_set - cur_set)

    logger.info(
        f"指数 {index_code} 调仓: {len(previous)}→{len(current)} "
        f"(+{len(added)}/-{len(removed)})"
    )
    if added:
        logger.info(f"  调入: {', '.join(added[:20])}{'...' if len(added) > 20 else ''}")
    if removed:
        logger.info(f"  调出: {', '.join(removed[:20])}{'...' if len(removed) > 20 else ''}")

    # 保存当前成分股快照
    store.save(prev_cache_key, pd.DataFrame({"code": current}), "meta")

    return {
        "index_code": index_code,
        "current_count": len(current),
        "previous_count": len(previous),
        "added": added,
        "removed": removed,
        "current": current,
    }

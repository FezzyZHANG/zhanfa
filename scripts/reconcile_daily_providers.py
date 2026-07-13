"""对代表性证券运行腾讯日线契约与性能基线检查。"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import sys
import time

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from zhanfa.data.daily_providers import (
    DAILY_COLUMNS,
    TencentDailyProvider,
    call_akshare,
    tencent_symbol,
)


STOCK_SAMPLES = {
    "沪主板": [
        "600519", "601318", "600036", "600276", "600000",
        "601398", "600887", "600030", "601012", "600309",
    ],
    "深主板": [
        "000001", "000333", "000858", "000651", "002594",
        "002415", "002230", "002475", "002714", "001979",
    ],
    "创业板": [
        "300750", "300059", "300124", "300015",
        "300274", "300308", "300347", "301269",
    ],
    "科创板": [
        "688001", "688981", "688111", "688036",
        "688012", "688599", "688256", "688041",
    ],
    "北交所": [
        "920002", "920008", "920016", "920019",
        "920099", "920118", "920128", "920167",
    ],
    "ST": ["000010", "000016", "000056", "000078"],
    "上市不满一年候选": ["001400", "603400", "301678", "688775"],
    "停牌/退市边界": ["000004", "000609"],
}
INDEX_SAMPLES = ["000300", "000001", "000905", "000852", "399006"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="20260701")
    parser.add_argument("--end", default="20260713")
    parser.add_argument("--adjust", choices=["", "qfq", "hfq"], default="")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument(
        "--limit", type=int, default=None, help="仅用于小样本性能基线"
    )
    parser.add_argument(
        "--compare-akshare-wrapper",
        action="store_true",
        help="对比 AKShare 腾讯包装器的日期、OHLC 与成交量",
    )
    args = parser.parse_args()

    samples = [
        (code, category, False)
        for category, codes in STOCK_SAMPLES.items()
        for code in codes
    ] + [(code, "指数", True) for code in INDEX_SAMPLES]
    if args.limit is not None:
        samples = samples[: max(1, args.limit)]
    stock_count = sum(not is_index for _, _, is_index in samples)
    if args.limit is None and stock_count < 50:
        raise RuntimeError(f"Reconciliation requires at least 50 stocks, got {stock_count}")

    started = time.monotonic()
    rows = []

    def check(code: str, category: str, is_index: bool) -> dict:
        provider = TencentDailyProvider()
        item = {"code": code, "category": category, "is_index": is_index}
        try:
            result = provider.fetch(
                code, args.start, args.end, args.adjust, is_index=is_index
            )
            frame = result.frame
            item.update(
                {
                    "ok": True,
                    "rows": len(frame),
                    "first_date": frame.index.min().date().isoformat(),
                    "last_date": frame.index.max().date().isoformat(),
                    "columns": list(frame.columns),
                    "contract_ok": list(frame.columns) == DAILY_COLUMNS,
                    "request_count": result.request_count,
                    "retry_count": result.retry_count,
                    "elapsed_seconds": round(result.elapsed_seconds, 4),
                }
            )
            if args.compare_akshare_wrapper:
                try:
                    reference = call_akshare(
                        "stock_zh_a_hist_tx",
                        symbol=tencent_symbol(code, is_index=is_index),
                        start_date=args.start,
                        end_date=args.end,
                        adjust=args.adjust,
                        timeout=10,
                    )
                    reference["date"] = pd.to_datetime(reference["date"])
                    reference = reference.set_index("date").rename(
                        columns={"amount": "volume"}
                    )
                    common = frame.index.intersection(reference.index)
                    tolerances = {
                        "open": 0.01,
                        "high": 0.01,
                        "low": 0.01,
                        "close": 0.01,
                        "volume": 0.01,
                    }
                    max_abs_diff = {
                        column: float(
                            (
                                frame.loc[common, column]
                                - pd.to_numeric(
                                    reference.loc[common, column], errors="coerce"
                                )
                            )
                            .abs()
                            .max()
                        )
                        for column in tolerances
                    }
                    item.update(
                        {
                            "reference_ok": bool(len(common))
                            and all(
                                max_abs_diff[column] <= tolerance
                                for column, tolerance in tolerances.items()
                            ),
                            "reference_common_rows": len(common),
                            "reference_max_abs_diff": max_abs_diff,
                        }
                    )
                except Exception as exc:
                    item.update({"reference_ok": False, "reference_error": str(exc)})
        except Exception as exc:
            item.update({"ok": False, "error": str(exc)})
        return item

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {
            executor.submit(check, code, category, is_index): (code, category)
            for code, category, is_index in samples
        }
        for future in as_completed(futures):
            rows.append(future.result())

    rows.sort(key=lambda item: (str(item["category"]), str(item["code"])))
    successes = [item for item in rows if item["ok"]]
    failures = [item for item in rows if not item["ok"]]
    output = {
        "start": args.start,
        "end": args.end,
        "adjust": args.adjust or "none",
        "stock_samples": stock_count,
        "index_samples": sum(is_index for _, _, is_index in samples),
        "successes": len(successes),
        "failures": len(failures),
        "failure_rate": round(len(failures) / len(rows), 6),
        "request_count": sum(int(item.get("request_count", 0)) for item in rows),
        "elapsed_seconds": round(time.monotonic() - started, 4),
        "reference_successes": sum(item.get("reference_ok") is True for item in rows),
        "reference_failures": sum(item.get("reference_ok") is False for item in rows),
        "items": rows,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

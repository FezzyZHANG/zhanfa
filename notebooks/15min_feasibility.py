"""
TICKET-027: 全A股 15 分钟级别价格数据存储可行性研究 — 测试脚本

测试内容:
  1. stock_zh_a_minute (Sina) API 能力
  2. 历史数据覆盖范围
  3. 限速触发阈值
  4. 盘中数据可用性
  5. parquet 文件大小实测
  6. stock_zh_a_hist_min_em (东方财富) 作为备选对比

用法: python notebooks/15min_feasibility.py
"""

import os
import sys
import time

# 解决 Windows GBK 终端下 akshare 返回 UTF-8 中文列名乱码问题
os.environ["PYTHONIOENCODING"] = "utf-8"

import pandas as pd
import akshare as ak

# ── 配置 ─────────────────────────────────────────────

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "feasibility_test")
SAMPLE_CODES = [
    ("000001", "sz"), ("000002", "sz"), ("600000", "sh"), ("600036", "sh"),
    ("600519", "sh"), ("000858", "sz"), ("601318", "sh"), ("600276", "sh"),
    ("000725", "sz"), ("002415", "sz"), ("300750", "sz"), ("601012", "sh"),
    ("600887", "sh"), ("000651", "sz"), ("002594", "sz"),
]
START_DATE = "20100101"
END_DATE = "21000101"


def code_to_sina(code: str) -> str:
    """将纯数字代码转为 Sina 格式: 60xxxx → sh600xxx, 其他 → szxxxxxx"""
    if code.startswith(("60", "68")):
        return f"sh{code}"
    return f"sz{code}"


def test_sina_api():
    """测试 1: stock_zh_a_minute (Sina) 基本能力"""
    print("=" * 60)
    print("测试 1: stock_zh_a_minute (Sina) API 基本能力")
    print("=" * 60)

    for period in ["1", "5", "15", "30", "60"]:
        t0 = time.time()
        try:
            df = ak.stock_zh_a_minute(symbol="sh600519", period=period, adjust="qfq")
            elapsed = time.time() - t0
            print(f"  period={period:3s}: {len(df):5d} 行, {elapsed:.2f}s, cols={list(df.columns)}")
        except Exception as e:
            print(f"  period={period:3s}: FAIL - {str(e)[:100]}")
        time.sleep(0.3)

    print("\n  注意: stock_zh_a_minute 列名已经是英文 (day/open/high/low/close/volume/amount)")
    print("  不需要像 daily fetcher 那样做中文列名映射")


def test_sina_history_window():
    """测试 2: Sina 数据历史覆盖范围 (多只股票)"""
    print("\n" + "=" * 60)
    print("测试 2: stock_zh_a_minute 历史数据覆盖范围")
    print("=" * 60)

    for code, _ in SAMPLE_CODES[:8]:
        sina_code = code_to_sina(code)
        try:
            df = ak.stock_zh_a_minute(symbol=sina_code, period="15", adjust="qfq")
            if len(df) > 0:
                first = df["day"].iloc[0]
                last = df["day"].iloc[-1]
                print(f"  {sina_code}: {len(df):5d} 行, {first} ~ {last}")
            else:
                print(f"  {sina_code}: 0 行")
        except Exception as e:
            print(f"  {sina_code}: FAIL - {str(e)[:100]}")
        time.sleep(0.3)


def test_sina_rate_limit():
    """测试 3: Sina 限速阈值 — 连续快速请求"""
    print("\n" + "=" * 60)
    print("测试 3: stock_zh_a_minute 限速探测 (连续请求 20 次)")
    print("=" * 60)

    results = []
    for i in range(20):
        t0 = time.time()
        try:
            df = ak.stock_zh_a_minute(symbol="sh600519", period="15", adjust="qfq")
            elapsed = time.time() - t0
            results.append((i + 1, "OK", elapsed, len(df)))
            print(f"    请求 {i+1:2d}: OK  ({elapsed:.2f}s, {len(df)} 行)")
        except Exception as e:
            elapsed = time.time() - t0
            results.append((i + 1, "FAIL", elapsed, str(e)[:80]))
            print(f"    请求 {i+1:2d}: FAIL ({elapsed:.2f}s) - {str(e)[:80]}")
            time.sleep(2)

    success = sum(1 for r in results if r[1] == "OK")
    ok_times = [r[2] for r in results if r[1] == "OK"]
    if ok_times:
        print(f"\n  成功率: {success}/{len(results)}, 平均耗时: {sum(ok_times)/len(ok_times):.2f}s")
    else:
        print(f"\n  成功率: {success}/{len(results)}")


def test_parquet_sizes():
    """测试 4: parquet 文件大小实测"""
    print("\n" + "=" * 60)
    print("测试 4: 数据量实测（parquet + snappy）")
    print("=" * 60)

    os.makedirs(OUT_DIR, exist_ok=True)

    total_rows = 0
    total_bytes = 0
    stats = []

    for i, (code, _) in enumerate(SAMPLE_CODES):
        sina_code = code_to_sina(code)
        try:
            df = ak.stock_zh_a_minute(symbol=sina_code, period="15", adjust="qfq")
            if "day" in df.columns:
                df["day"] = pd.to_datetime(df["day"])
                df = df.set_index("day")

            fpath = os.path.join(OUT_DIR, f"{code}.parquet")
            df.to_parquet(fpath, compression="snappy")
            fsize = os.path.getsize(fpath)
            stats.append({"code": code, "rows": len(df), "bytes": fsize})
            total_rows += len(df)
            total_bytes += fsize
            print(f"  [{i+1:2d}/{len(SAMPLE_CODES)}] {code}: {len(df):6d} 行, {fsize/1024:8.1f} KB")
        except Exception as e:
            print(f"  [{i+1:2d}/{len(SAMPLE_CODES)}] {code}: FAIL - {str(e)[:80]}")

        time.sleep(0.3)

    if total_rows > 0:
        avg_bpr = total_bytes / total_rows  # bytes per row
        print(f"\n  总计: {total_rows} 行, {total_bytes/1024/1024:.2f} MB")
        print(f"  平均每行: {avg_bpr:.1f} bytes")
        print(f"\n  预估 (基于实测 avg {avg_bpr:.1f} bytes/行):")
        # 5,200 stocks × 16 rows/day × 242 days
        one_year_rows = 5200 * 16 * 242
        print(f"  全市场 1 年: {one_year_rows * avg_bpr / 1024 / 1024:.0f} MB ({one_year_rows:,} 行)")
        print(f"  全市场 3 年: {one_year_rows * 3 * avg_bpr / 1024 / 1024 / 1024:.1f} GB")
        print(f"  全市场 5 年: {one_year_rows * 5 * avg_bpr / 1024 / 1024 / 1024:.1f} GB")
        print(f"  全市场 10 年: {one_year_rows * 10 * avg_bpr / 1024 / 1024 / 1024:.1f} GB")


def test_em_api():
    """测试 5: stock_zh_a_hist_min_em (东方财富) 作为对比"""
    print("\n" + "=" * 60)
    print("测试 5: stock_zh_a_hist_min_em (东方财富) 对比")
    print("=" * 60)

    for code in ["000001", "600519", "300750"]:
        try:
            df = ak.stock_zh_a_hist_min_em(
                symbol=code, start_date="2020-01-01 09:30:00",
                end_date="2026-05-05 15:00:00", period="15", adjust="qfq"
            )
            if len(df) > 0:
                # 列名是中文 UTF-8，映射为英文
                col_map = {
                    "时间": "time", "开盘": "open", "收盘": "close",
                    "最高": "high", "最低": "low", "成交量": "volume",
                    "成交额": "amount", "涨跌幅": "pct_chg", "涨跌额": "chg",
                    "振幅": "amplitude", "换手率": "turnover",
                }
                df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
                print(f"  {code}: {len(df)} 行, cols={list(df.columns)}")
                print(f"         first={df['time'].iloc[0]}, last={df['time'].iloc[-1]}")
            else:
                print(f"  {code}: 0 行")
        except Exception as e:
            print(f"  {code}: FAIL - {str(e)[:100]}")
        time.sleep(0.3)


def test_intraday_availability():
    """测试 6: 盘中数据可用性"""
    print("\n" + "=" * 60)
    print("测试 6: 盘中数据可用性")
    print("=" * 60)

    from datetime import datetime
    now = datetime.now()
    is_trading = (
        now.weekday() < 5
        and ((9, 30) <= (now.hour, now.minute) < (11, 30) or (13, 0) <= (now.hour, now.minute) < (15, 0))
    )
    print(f"  当前时间: {now}")
    print(f"  交易时段: {'是' if is_trading else '否'}")

    for raw_code in ["000001", "600519"]:
        sina_code = code_to_sina(raw_code)
        try:
            df = ak.stock_zh_a_minute(symbol=sina_code, period="15", adjust="qfq")
            latest = df["day"].iloc[-1] if len(df) > 0 else "N/A"
            print(f"  {sina_code}: {len(df)} 行, 最新: {latest}")
        except Exception as e:
            print(f"  {sina_code}: FAIL - {str(e)[:100]}")
        time.sleep(0.3)


def test_data_structure():
    """测试 7: 数据结构细节"""
    print("\n" + "=" * 60)
    print("测试 7: 15min 数据结构检查")
    print("=" * 60)

    df = ak.stock_zh_a_minute(symbol="sh600519", period="15", adjust="qfq")
    print(f"  列名: {list(df.columns)}")
    print(f"  类型:\n{df.dtypes}")
    print(f"  数值范围:")
    for col in ["open", "high", "low", "close"]:
        print(f"    {col}: {df[col].min():.2f} ~ {df[col].max():.2f}")
    # volume/amount 是字符串，需转换后查看
    vol_num = pd.to_numeric(df["volume"], errors="coerce")
    amt_num = pd.to_numeric(df["amount"], errors="coerce")
    print(f"    volume: {vol_num.min():.0f} ~ {vol_num.max():.0f}")
    print(f"    amount: {amt_num.min():.0f} ~ {amt_num.max():.0f}")
    print(f"  零成交量的行: {(df['volume'] == 0).sum()} / {len(df)}")
    print(f"  时间间隔: {df['day'].diff().value_counts().head(5).to_dict()}")


# ── 主流程 ────────────────────────────────────────────

if __name__ == "__main__":
    print("TICKET-027 可行性研究 — 测试脚本")
    print(f"样本股票: {len(SAMPLE_CODES)} 只")
    print(f"输出目录: {OUT_DIR}")
    print()

    test_sina_api()
    time.sleep(0.5)

    test_sina_history_window()
    time.sleep(0.5)

    test_sina_rate_limit()
    time.sleep(0.5)

    test_parquet_sizes()
    time.sleep(0.5)

    test_em_api()
    time.sleep(0.5)

    test_intraday_availability()
    time.sleep(0.5)

    test_data_structure()

    print("\n" + "=" * 60)
    print("测试完成。结果供撰写报告使用。")
    print("=" * 60)

# TICKET-024: 数据管理后端 — 统计与刷新 API

**优先级:** P1 - 高
**状态:** ✅ 已完成
**依赖:** -
**预计工时:** 0.5d

## 需求描述

当前系统没有提供数据状态的可见性——用户不知道缓存了多少只股票、数据覆盖什么时间范围、最新数据到哪一天。需要一组后端 API 来暴露数据统计信息，并提供手动触发数据刷新的能力。

现有的 `/api/scheduler/trigger` 端点（[scheduler.py](../../src/zhanfa/api/routers/scheduler.py)）只支持 `update_daily` 和 `rebalance_index` 两种 action，需要增强为更灵活的"抓取至今"能力。

## 功能清单

### 1. 数据统计 API — `GET /api/data/stats`

返回缓存和数据库的整体状态：

```python
# 返回模型
class DataStats:
    # 缓存统计
    cache: CacheStats       # parquet 缓存状态
    # 数据库统计
    database: DBStats       # 关系数据库状态

class CacheStats:
    stock_count: int        # 已缓存的股票数（daily/*.parquet）
    total_rows: int         # 所有缓存数据总行数
    storage_bytes: int      # 缓存目录总大小
    date_range: DateRange   # 全市场最早/最晚日期
    freq_stats: dict[str, int]  # 各频率缓存数 {"daily": 4523, "financial": 3200}

class DBStats:
    stock_count: int        # stocks 表记录数
    financial_count: int    # stock_financial 表记录数
    watchlist_count: int    # watchlists 表记录数
    strategy_count: int     # strategies 表记录数
    backtest_count: int     # backtest_results 表记录数
```

实现位置: [store.py](../../src/zhanfa/data/store.py) 新增 `stats()` 方法扫描 parquet 目录；[models.py](../../src/zhanfa/db/models.py) 对应表执行 `SELECT COUNT(*)`。

### 2. 单股票数据状态 — `GET /api/data/stock-status?code=XXX`

```python
class StockDataStatus:
    code: str
    name: str
    has_daily: bool
    daily_start: date | None
    daily_end: date | None
    daily_rows: int
    has_financial: bool
    financial_start: date | None
    financial_end: date | None
    financial_rows: int
    in_watchlist: list[str]   # 所属自选股组名列表
```

### 3. 数据刷新 API — `POST /api/data/refresh`

增强现有 scheduler trigger，提供更灵活的控制：

```python
class RefreshRequest:
    codes: list[str] | None     # None = 刷新全部已缓存股票
    freq: str = "daily"         # 刷新频率
    force: bool = False         # 是否强制重拉（忽略缓存）
    discover_new: bool = True   # 是否自动发现新上市股票
    max_new: int = 50

class RefreshResult:
    updated: int
    failed: int
    new_discovered: int
    errors: list[dict]          # 失败详情 [{code, error}]
```

核心逻辑：`force=True` 时先删除对应 parquet 文件再调用 `Fetcher.daily()`，触发 akshare 重新拉取。

### 4. 路由注册

新建 `src/zhanfa/api/routers/data.py`，在 [api/__init__.py](../../src/zhanfa/api/__init__.py) 中注册。

## 验收标准

- [ ] `GET /api/data/stats` 返回正确的缓存和数据库统计
- [ ] `GET /api/data/stock-status?code=600519` 返回单股票数据状态
- [ ] `POST /api/data/refresh` 能增量更新（无 force）和强制全量刷新（force=True）
- [ ] 缓存为空时 stats 不报错，返回 0 值
- [ ] Swagger 文档 (`/docs`) 中可见新端点
- [ ] 单测覆盖 stats 和 refresh 逻辑

## 备注

- `CacheStats.date_range` 通过抽样读取 parquet 文件头尾实现，而非全量扫描（避免 OOM）
- 刷新操作可能耗时很长（全市场数千只股票），建议返回后异步执行，通过 `/api/scheduler/status` 轮询进度
- `force=True` 时注意先备份旧文件或保留旧数据直到新数据写入成功

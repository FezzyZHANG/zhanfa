# 数据获取与管线

## 数据流

```
腾讯/akshare 日线 Provider ─┐
akshare 元数据/财务/Sina 分钟线 ─┴→ Fetcher → Store (parquet + 来源元数据)
                                      → Pipeline → Strategy / Backtest
```

## Fetcher — 数据获取

日线通过最小 Provider 边界访问腾讯或 akshare；股票列表、成分股、财务和分钟线继续使用 akshare 的现有能力。所有方法自动缓存，首次走网络，之后走本地 parquet。

### 网络代理默认行为

`Fetcher` 调用 akshare 时默认不继承当前进程的系统代理环境变量，避免
`HTTP_PROXY` / `HTTPS_PROXY` 等宿主配置把东方财富、Sina 等数据源请求转发到
本地代理后产生 `ProxyError`。如确需通过代理访问数据源，可设置
`ZHANFA_AKSHARE_USE_PROXY=true` 显式开启代理继承。腾讯直连同样默认不继承系统代理；确需代理时设置 `ZHANFA_TENCENT_USE_PROXY=true`。

| 方法 | 返回 | 缓存位置 | 说明 |
|---|---|---|---|
| `daily(code, start="20180101")` | DataFrame | `data/daily/{code}.parquet` | 个股日线（默认前复权） |
| `daily_batch(codes)` | dict[str, DF] | 同上批量 | 批量获取 |
| `minute(code, period="60")` | DataFrame | `data/minute_{period}/{code}.parquet` | 分钟级数据（1h/15min/30min，Sina 源） |
| `minute_batch(codes, period)` | dict[str, DF] | 同上批量 | 批量获取分钟数据 |
| `index_daily(code)` | DataFrame | `data/index_daily/{code}.parquet` | 指数日线 |
| `index_components(code)` | list[str] | `data/meta/components_{code}.parquet` | 指数成分股代码 |
| `stock_list()` | DataFrame | `data/meta/stock_list.parquet` | 全 A 股列表 |
| `financial(code)` | DataFrame | `data/financial/{code}.parquet` | 财务指标（标准化） |

### 日线数据

```python
from zhanfa.data.fetcher import Fetcher

fetcher = Fetcher()
df = fetcher.daily("000001")           # 平安银行日线
hs300 = fetcher.index_daily("000300")  # 沪深300指数
batch = fetcher.daily_batch(["000001", "000002"])  # 批量
```

本地非商业研究模式默认使用腾讯直连日线。设置 `ZHANFA_DAILY_PROVIDER=akshare` 可一键恢复原路径；`ZHANFA_DAILY_FALLBACK_ENABLED=false` 可关闭跨 Provider 回退。商业、公开或生产用途必须先完成授权评估，未显式接受风险时腾讯 Provider 会拒绝启动。

返回的 DataFrame 列名为 `open, high, low, close, volume, amount, turnover`，单位依次为元、手、万元和百分数（`1.25` 表示 1.25%），index 为升序、去重的 `DatetimeIndex`。默认查询从 2018-01-01 开始；调用方仍可显式传入更早日期。无论命中旧缓存还是网络返回，结果都会严格裁剪到 `start/end`。

腾讯 Provider 支持沪、深、北交所和指数代码，`920002` 映射为 `bj920002`，不经过 AKShare 对北交所会失败的起始日期探测。字段、样本和性能基线见[腾讯日线 Provider 数据对账报告](../developer/reports/tencent-data-reconciliation.md)。

### 分钟级数据

```python
from zhanfa.data.fetcher import Fetcher

fetcher = Fetcher()

# 1 小时线（推荐，~2 年历史）
df_1h = fetcher.minute("000001", period="60")

# 15 分钟线（~6 个月历史）
df_15min = fetcher.minute("000001", period="15")

# 30 分钟线（~1 年历史）
df_30min = fetcher.minute("000001", period="30")

# 批量获取
batch = fetcher.minute_batch(["000001", "600519"], period="60")
```

数据源为 Sina `stock_zh_a_minute`，固定返回 1,970 行。频率越低覆盖历史越久（1h ~2 年，15min ~6 月）。列名：`open, high, low, close, volume, amount`，index 为 `DatetimeIndex`。

缓存目录：`data/minute_60/`、`data/minute_15/`、`data/minute_30/`。

### 成分股与全市场

```python
codes = fetcher.index_components("000300")  # ['000001', '000002', ...]
all_stocks = fetcher.stock_list()           # DataFrame[code, name]
```

这些元数据变更频率低，缓存后很少触发网络请求。

### 财务数据

```python
fin = fetcher.financial("000001")
fin.columns  # ['net_profit', 'net_profit_yoy', 'eps', 'bvps', 'roe', 'debt_ratio', ...]
```

akshare 原始返回的中文列名（净利润、资产负债率...）和中文单位（亿/万/%）在 `_clean_financial()` 中统一转为英文列名 + float64 数值。

| 原始列名 | 标准化后 | 类型 |
|---|---|---|
| 净利润 | `net_profit` | float64 |
| 净利润同比增长率 | `net_profit_yoy` | float64 |
| 扣非净利润 | `net_profit_deducted` | float64 |
| 营业总收入 | `revenue` | float64 |
| 基本每股收益 | `eps` | float64 |
| 每股净资产 | `bvps` | float64 |
| 净资产收益率 | `roe` | float64 |
| 资产负债率 | `debt_ratio` | float64 |
| 销售净利率 | `net_margin` | float64 |
| 毛利率 | `gross_margin` | float64 |
| 流动比率 | `current_ratio` | float64 |
| 速动比率 | `quick_ratio` | float64 |
| 股息率 | `dividend_yield` | float64 |
| 市盈率 | `pe` | float64 |
| 市净率 | `pb` | float64 |
| ... | (共 25 列) | float64 |

## Pipeline — 数据清洗

| 方法 | 说明 |
|---|---|
| `clean(df)` | 去停牌（零成交量）、去 NaN/Inf、排序 |
| `align(multi)` | 多标的日期对齐，返回 price DataFrame + returns dict |
| `compute_returns(df)` | 计算日收益率 |
| `add_simple_indicators(df)` | 批量添加技术指标（12 列） |
| `train_test_split(df, date)` | 按日期切分训练/测试集 |

### 技术指标清单

`add_simple_indicators()` 添加以下列：

| 新增列 | 含义 |
|---|---|
| `sma_20`, `sma_60`, `sma_120` | 简单移动均线 |
| `vol_sma_20` | 成交量均线 |
| `channel_pct` | 20 日通道位置百分比 |
| `ret_1d`, `ret_5d`, `ret_20d` | 1/5/20 日收益率 |
| `volatility_20d` | 20 日波动率 |
| `atr_14` | 14 日 ATR |
| `high_20`, `low_20` | 20 日最高/最低价 |

## Store — 本地缓存

```python
from zhanfa.data.store import Store

store = Store(base_dir="data")  # 默认目录

store.save("000001", df)              # 保存
store.save("000001", df, freq="weekly")  # 指定频率
df = store.load("000001")             # 加载
exists = store.exists("000001")       # 检查
codes = store.codes("daily")          # 列出已缓存代码
store.delete("000001")                # 删除缓存
store.save_batch({"A": df1, "B": df2})  # 批量保存
stats = store.stats()                 # 缓存统计（股票数、行数、日期范围等）
```

### 缓存统计

`Store.stats()` 返回缓存目录的整体状态：

```python
{
    "stock_count": 4523,              # 已缓存股票数
    "total_rows": 12_000_000,         # 总数据行数
    "storage_bytes": 500_000_000,     # 总存储大小（字节）
    "date_range": {                   # 全市场日期范围（通过采样获取）
        "start": date(2010, 1, 5),
        "end": date(2026, 5, 4),
    },
    "freq_stats": {                   # 各频率缓存文件数
        "daily": 4523,
        "financial": 3200,
        "index_daily": 5,
        "meta": 3,
    },
}
```

日期范围通过读取每个 parquet 文件的头尾行抽样获取，避免全量扫描导致 OOM。

### 缓存 TTL 与自动刷新

`Store.load()` 支持 `max_age` 参数（`timedelta | None`），基于文件修改时间（mtime）判断缓存是否过期。`Fetcher` 各方法已配置合理的默认 TTL：

| 方法 | 默认 TTL | 环境变量覆盖 |
|---|---|---|
| `daily()` | 6h | `CACHE_TTL_DAILY_HOURS` |
| `index_daily()` | 6h | `CACHE_TTL_INDEX_DAILY_HOURS` |
| `stock_list()` | 24h | `CACHE_TTL_STOCK_LIST_HOURS` |
| `index_components()` | 24h | `CACHE_TTL_INDEX_COMPONENTS_HOURS` |
| `industry_stocks()` | 24h | `CACHE_TTL_INDUSTRY_STOCKS_HOURS` |
| `financial()` | 30d | `CACHE_TTL_FINANCIAL_HOURS` |
| `minute()` | 6h | `CACHE_TTL_MINUTE_HOURS` |

日线缓存过期后不会默认重拉 2018 年至今：Fetcher 从缓存最大日期前 7 天开始重叠增量抓取、按日期去重后原子覆盖 parquet。前复权缓存默认每 30 天做一次同 Provider 全量校准；来源或复权方式变化时也执行全量覆盖，禁止把不同来源的复权片段静默拼接。

### 缓存完整性校验

- `stock_list()`: 加载缓存后检查行数 ≥5000，防止截断数据。不满足时自动删除坏缓存并重新拉取。
- `daily()`: 加载缓存后检查行数 ≥1，空缓存自动修复；空网络响应和双 Provider 失败不会写入缓存。

### 缓存可知情

- `Store.mtime(code, freq)` 返回缓存文件的最后修改时间（UTC）。
- `GET /api/data/stats` 返回 `last_refreshed_at` — 全局最新缓存刷新时间。
- `GET /api/data/stock-status?code=XXX` 返回每种频率的 `cached_at` — 该股票各频率缓存的最后修改时间。
- 前端 DataPage 显示缓存更新时间（相对时间 + 绝对时间），QuoteItem 的 `data_freshness` 字段反映数据年龄（`cached_2h`、`cached_3d`、`stale` 等）。

### 调度器自动刷新

FastAPI 启动时自动注册定时任务：

| 任务 | 时间 | 说明 |
|---|---|---|
| `update_daily_data` | 每日 15:30 | 更新所有已缓存日线 + 发现新上市股票 |
| `update_minute_data` | 每日 15:45 | 更新所有已缓存分钟线 |
| `weekly_index_rebalance` | 每周五 16:00 | 对比沪深300新旧成分股并记录变更 |

`GET /api/scheduler/status` 查看任务列表、运行状态、最近错误和下次执行时间。

缓存文件结构：
```
data/
├── daily/          {code}.parquet + {code}.meta.json
├── minute_60/      {code}.parquet    （1h 线）
├── minute_15/      {code}.parquet    （15min 线）
├── minute_30/      {code}.parquet    （30min 线）
├── index_daily/    {code}.parquet + {code}.meta.json
├── financial/      {code}.parquet
└── meta/           components_{code}.parquet, stock_list.parquet
```

## 分钟级数据

详见 [分钟级数据存储可行性报告](../developer/reports/15min-feasibility.md)。

**后端已实现**: `Fetcher.minute(code, period)` 支持 `"15"/"30"/"60"` 三种频率，Sina `stock_zh_a_minute` 数据源。`Pipeline.clean()` 已适配字符串型 volume/amount 转换。存储沿用 `Store` 的 freq 子目录机制。

**API 已支持**: `GET /api/stocks/{code}/daily?freq=60min|30min|15min` 直接返回分钟级 K 线数据。`GET /api/data/stock-status?code=XXX` 返回 `minute_60/minute_30/minute_15` 缓存状态。

**前端已支持**: `ChartToolbar` 提供 1h/30min/15min 按钮，选择后自动从服务端获取分钟数据，无需客户端聚合。分钟数据保留完整时间戳（ISO 8601）。

**核心结论**: Sina `stock_zh_a_minute` 支持 1/5/15/30/60min 频率，固定返回 1,970 行。频率越低（bar 越长），覆盖历史越久：

| 频率 | bar/天 | 历史深度 | 全市场存储 |
|------|--------|---------|-----------|
| **1h (60min)** | 4 | **~2 年** | ~660 MB |
| 15min | 16 | ~6 个月 | ~460 MB |
| 1min | 240 | ~1.5 周 | — |

**推荐**: 优先支持 1h 数据（2 年历史 + 低存储成本，可做中等长度回测），15min 作为补充。

**关键限制**: 免费数据源均受限于服务端返回行数/时间窗口，无法获取分钟级全量历史。长期回测仍需依赖日线（`stock_zh_a_hist`，26 年覆盖）。如未来需要更长分钟级历史，需考虑付费数据源（JoinQuant/Tushare Pro/Wind）。

## 添加新数据源

日线来源在 `daily_providers.py` 中实现 `DailyProvider.fetch()`，由 `Fetcher` 统一处理缓存、增量、回退和状态；不要把来源判断散落到 service 或 workflow。其他能力新增方法时仍遵循：优先读缓存、标准化列和单位、验证非空后原子保存。

## 关系数据库

K 线行情数据保留在 parquet 中（数据量大），结构化数据（策略、自选股、回测结果）使用 SQLAlchemy ORM + SQLite/PostgreSQL。

### 表结构

| 表名 | 说明 |
|---|---|
| `strategies` | 策略/流派注册表，含参数快照和 Python 类路径 |
| `stocks` | 股票元信息（代码、名称、行业、市值等） |
| `stock_financial` | 财报数据缓存，按 `(code, report_date)` 唯一 |
| `watchlists` | 自选股分组 |
| `watchlist_items` | 自选股明细，级联删除 |
| `backtest_results` | 回测结果，含参数快照、指标 JSON、净值/回撤/交易时序数据、Markdown 报告、task_id 全局标识 |

### 数据库迁移

```bash
# 一键建表
uv run alembic upgrade head

# 生成新迁移（修改模型后）
uv run alembic revision --autogenerate -m "描述"
```

数据库文件位于 `data/zhanfa.db`（SQLite）。

### 数据导入

```python
from zhanfa.db.import_data import import_all, import_stocks, import_financials

import_all()  # 一键导入股票和财报
```

从 `data/meta/stock_list.parquet` 导入股票元信息，从 `data/financial/*.parquet` 导入财报数据。重复执行幂等。

`POST /api/data/initialize` 会先通过 akshare 拉取并缓存全 A 股列表，再把股票元信息导入 `stocks` 表。数据管理页的“初始化数据”按钮调用该接口，适合空数据库首次使用。

### 策略注册

```python
from zhanfa.db.register_strategies import register_strategies

registered = register_strategies()
# ['zhanfa.strategies.trend.sma_cross.SMACross', 'zhanfa.strategies.trend.turtle.Turtle']
```

自动扫描 `zhanfa.strategies` 包中所有 `BaseStrategy` 子类，提取名称、类别、文档、默认参数，注册到 `strategies` 表。重复执行幂等。

### 使用示例

```python
from zhanfa.db.base import SessionLocal
from zhanfa.db.models import Stock, Strategy, StockFinancial, BacktestResult

session = SessionLocal()

# 查询股票
stock = session.get(Stock, "000001")

# 查询某股票最新财报
fin = (session.query(StockFinancial)
       .filter_by(code="000001")
       .order_by(StockFinancial.report_date.desc())
       .first())

# 查询所有趋势策略
trends = session.query(Strategy).filter_by(category="trend").all()
session.close()
```

## 数据管理 API

### 数据统计 — `GET /api/data/stats`

返回缓存和数据库的整体状态，包括缓存股票数、总行数、存储大小、日期范围、数据库各表记录数。

### 单股票状态 — `GET /api/data/stock-status?code=XXX`

查询单只股票的缓存状态：日线有无/起止日期/行数、Provider、复权方式、最近请求/重试数，财务数据有无/起止日期/行数，以及所属自选股组。

### 数据刷新 — `POST /api/data/refresh`

手动触发数据更新：

```json
{
    “codes”: [“000001”, “600519”],  // null = 全部已缓存股票
    “freq”: “daily”,                // daily | minute_60 | minute_30 | minute_15
    “force”: false,                 // true = 强制删除缓存后重拉
    “discover_new”: true,           // 自动发现新上市股票（仅 daily 有效）
    “max_new”: 50                   // 仅 daily 有效
}
```

返回 `{“updated”: 2, “failed”: 0, “new_discovered”: 3, “deferred”: 0, “providers”: {“000001”: “tencent”}, “errors”: []}`；达到单次证券硬上限时，`deferred` 表示留待后续批次的数量。

默认 `discover_new=true` 时，刷新流程会先拉取全 A 股列表并同步写入 `stocks` 表，然后再发现并拉取未缓存股票的日线数据。因此空库首次点击”抓取至今”后，自选股添加所需的股票元信息会自动补齐。

`force=true` 时先删除目标频率对应的 parquet 文件再拉取，确保数据刷新。

`freq` 为分钟级（`minute_60`/`minute_30`/`minute_15`）时，刷新调用 `Fetcher.minute(code, period=…)` 拉取对应周期的分钟线数据。未知 `freq` 值返回 400。

### 自选股与股票元信息

`watchlist_items.code` 外键指向 `stocks.code`。为了避免空库或局部数据环境下添加自选股失败，后端在添加单只或批量自选股前会确保对应 `Stock` 记录存在；若 `stocks` 表暂未初始化，会从全 A 股列表中查找名称并创建最小股票元信息。

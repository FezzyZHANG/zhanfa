# 架构设计

## 分层架构

```
┌──────────────────────────────────────────────┐
│            scripts / notebooks               │  ← 用户入口
├──────────────────────────────────────────────┤
│                   api/                       │  ← FastAPI REST 服务
│   routers/   services/   models.py           │
│   database.py                               │
├──────────────────────────────────────────────┤
│    automation/          jq/                  │  ← 自动化 & 云端验证
├──────────────────────────────────────────────┤
│                   db/                        │  ← ORM 模型 & 数据导入
│   models.py  base.py  import_data.py         │
│   register_strategies.py                     │
├──────────────────────────────────────────────┤
│               backtest/                      │  ← vectorbt 封装
├──────────────────────────────────────────────┤
│              strategies/                     │  ← 策略库（按流派组织）
│   trend/   momentum/   fundamental/  ...     │
├──────────────────────────────────────────────┤
│                data/                         │  ← 数据管线
│   fetcher.py  pipeline.py  store.py          │
└──────────────────────────────────────────────┘
```

数据流自底向上：`akshare API → Fetcher → Pipeline → Store (parquet) → Strategy → Backtest → API / CLI`
API 调用路径：`HTTP → routers → services → db (ORM) / data / strategies / backtest 模块`
持久化：`API/CLI → db (SQLAlchemy ORM) → SQLite (data/zhanfa.db)` + `parquet 文件 (K 线)`

## 模块职责

### data/ — 数据层

| 文件 | 职责 |
|---|---|
| `fetcher.py` | akshare 封装，日线/指数/财报/成分股，统一返回标准化 DataFrame |
| `pipeline.py` | 清洗（去停牌/NaN/复权对齐）、特征计算（均线/ATR/波动率）、切分 |
| `store.py` | 本地 parquet 缓存，按 `{freq}/{code}.parquet` 组织 |

所有 Fetcher 方法**首次调用走 akshare API，之后自动读本地缓存**。缓存分区：

| freq | 内容 |
|---|---|
| `daily` | 个股日线 |
| `index_daily` | 指数日线 |
| `financial` | 财务数据（列名已标准化为英文） |
| `meta` | 成分股列表、全A股列表等元数据 |

### strategies/ — 策略层

按交易流派分目录：
- `trend/` — 趋势跟踪（双均线、海龟）
- `momentum/` — 动量/反转
- `fundamental/` — 基本面（央企高股息...）
- `composite/` — 多因子综合

所有策略继承 `BaseStrategy`，实现 `generate_signals(data) → pd.Series[bool]`。

内部不依赖任何运行环境，可同时用于本地 vectorbt 回测和 JoinQuant 云端仿真。

### backtest/ — 回测层

| 文件 | 职责 |
|---|---|
| `engine.py` | 封装 `vbt.Portfolio.from_signals()`，支持单策略、多策略对比和多资产组合回测 |
| `metrics.py` | 夏普比率、最大回撤、卡玛比率、索提诺比率等 |
| `report.py` | Markdown 格式回测报告生成 |

### jq/ — JoinQuant 适配

将本地策略翻译为 JoinQuant 的 `initialize()` + `handle_data()` 代码骨架。用户填入具体买卖逻辑后即可在聚宽平台运行。

> `to_jq_template()` 自动生成结构化的 JQ 交易代码——包含参数变量声明、条件提示和完整的买卖执行逻辑，用户仅需填入具体的信号判断条件。

### db/ — 数据库层

| 文件 | 职责 |
|---|---|
| `base.py` | SQLAlchemy 引擎、会话工厂、建表 |
| `models.py` | ORM 模型（Strategy / Stock / StockFinancial / Watchlist / WatchlistItem / BacktestResult） |
| `import_data.py` | 从 parquet 缓存批量导入股票元信息和财报到数据库 |
| `register_strategies.py` | 启动时自动扫描策略类并注册到 strategies 表 |

### api/ — REST API 服务

| 文件 | 职责 |
|---|---|
| `__init__.py` | FastAPI app 入口，`uv run uvicorn zhanfa.api:app` |
| `models.py` | Pydantic v2 请求/响应 schema |
| `database.py` | 数据库访问层统一导出（模型和会话定义在 `db/` 中） |
| `routers/` | 路由处理器（策略、股票、自选股、回测、调度） |
| `services/` | 业务逻辑层，复用 data/strategies/backtest 模块 |

API 端点：

| 路由 | 端点 | 说明 |
|---|---|---|
| `/api/strategies` | 5 个端点 | 策略发现、CRUD、参数管理 |
| `/api/stocks` | 6 个端点 | 股票列表、元信息、K 线、财报、技术指标、行业对比 |
| `/api/watchlists` | 14 个端点 | 自选股分组 CRUD、股票搜索/添加/移除/备注、行情查询（缓存优先+数据状态）、批量操作（含预览/批量删除）、CSV导出 |
| `/api/backtest` | 4 个端点 | 回测提交（异步）、状态查询、历史记录、多结果对比 |
| `/api/scheduler` | 2 个端点 | 调度状态、手动触发 |
| `/api/data` | 3 个端点 | 数据统计、单股票状态查询、数据刷新 |

K 线行情数据保留在 parquet 中（数据量大，已有成熟 Store 层）。关系数据库仅管理自选股等结构化数据。通过 SQLAlchemy 实现数据库无关访问，开发用 SQLite、生产可切换 PostgreSQL。

数据库文件：`data/zhanfa.db`（SQLite）

### automation/ — 自动化

定时调度器 + 工作流（数据更新、成分股刷新）。详见 [automation.md](automation.md)。

**工作流** (`workflows.py`):

| 函数 | 说明 |
|------|------|
| `update_daily_data(codes, discover_new, max_new)` | 日数据更新，可选自动发现新上市股票并拉取 |
| `weekly_index_rebalance(index_code)` | 指数调仓对比，记录调入/调出变更 |

**调度器** (`scheduler.py`):

| 特性 | 说明 |
|------|------|
| `@daily("HH:MM")` | 每日定时执行 |
| `@hourly()` | 每小时执行 |
| `state_file` | JSON 状态持久化，重启后恢复 |
| `on_error` | 错误通知回调 |
| `run_loop()` / `run_pending()` | 阻塞循环 / 单次非阻塞执行 |

```python
from zhanfa.automation.scheduler import Scheduler

scheduler = Scheduler(
    state_file="data/schedule.json",
    on_error=lambda job, exc: print(f"[ALERT] {job} failed: {exc}"),
)

@scheduler.daily("17:00")
def update_data():
    update_daily_data()

scheduler.run_loop()  # 阻塞运行
```

> **当前状态**: `Scheduler` 类的 `state_file` 和 `on_error` 接口已实现，但模块级默认实例未经配置且 API 进程未启动后台循环。详见 [automation.md](automation.md) 中的"当前限制"章节。

## 关键设计决策

### 1. src layout

包放在 `src/zhanfa/` 下。开发时 uv 自动以 editable 模式安装，`from zhanfa.xxx` 可直接使用，无需 `sys.path` 拐杖。

### 2. 策略接口统一

`generate_signals(data) → pd.Series[bool]`，输出直接喂给 `vbt.Portfolio.from_signals()`。不耦合 vectorbt 或 JoinQuant。

### 3. 全量本地缓存

所有 akshare 调用结果自动缓存为 parquet，后续运行秒级读取，不受 API 频次限制。

### 4. 中英文列名标准化

akshare 返回的中文列名在 fetcher 层统一转英文（`_clean_ohlcv` / `_clean_financial`），中文单位（亿/万/%）转为 float。下游代码只看到英文列名和数值类型。

## 部署

### 开发环境一键启动

```bash
# 后端 (含自动重载)
uv run uvicorn zhanfa.api:app --reload --host 0.0.0.0 --port 8000

# 前端 (含 HMR)
cd frontend && npm run dev  # → http://localhost:5173
```

Vite 开发服务器已配置 `/api` 代理转发到后端 8000 端口，无 CORS 问题。

### Docker Compose 部署

```bash
docker compose up -d
```

服务组成：
- **backend** — FastAPI + uvicorn, 端口 8000
- **frontend** — nginx 静态文件服务, 端口 80，API 请求反向代理到 backend
- **db** — PostgreSQL 16, 端口 5432

数据目录 `data/` 和 PostgreSQL 数据通过 Docker volume 持久化。

### 代码质量

| 工具 | 用途 |
|------|------|
| ruff | Python lint + format |
| mypy | Python 类型检查 |
| pytest | 单元测试 |
| prettier | 前端格式化 |
| eslint | 前端 lint |
| vitest | 前端测试 |

pre-commit hooks 配置在 `.pre-commit-config.yaml`，CI 通过 GitHub Actions 自动运行。

# 系统架构设计

## 整体架构图

```
┌─────────────────────────────────────────────────────────┐
│                      前端 (Browser)                      │
│  React 18 + TypeScript + Vite                           │
│  ├── TradingView Lightweight Charts  ← K 线             │
│  ├── ECharts                        ← 财报图表          │
│  ├── Ant Design / shadcn/ui         ← UI 框架           │
│  └── React Router / TanStack Router ← 路由              │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP REST / WebSocket
┌──────────────────────▼──────────────────────────────────┐
│                   后端 API (Python)                       │
│  FastAPI + Pydantic v2                                   │
│  ├── /api/strategies    ← 流派 CRUD                      │
│  ├── /api/stocks        ← 股票数据 (K 线、财报)          │
│  ├── /api/watchlist     ← 自选股管理                     │
│  ├── /api/backtest      ← 回测执行与结果                 │
│  ├── /api/scheduler     ← 任务调度控制                   │
│  └── /api/data          ← 数据统计与刷新                 │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                   数据层                                  │
│  ├── PostgreSQL / SQLite  ← 结构化数据                   │
│  │   - strategies, stocks, financials, watchlists,        │
│  │     backtest_results                                   │
│  ├── Parquet 文件          ← 历史 K 线 (保持不变)        │
│  └── DailyProvider / akshare ← 外部数据源                │
└─────────────────────────────────────────────────────────┘
```

### 日线 Provider 边界

`src/zhanfa/data/daily_providers.py` 定义股票/指数共用的最小 `DailyProvider.fetch()` 契约。腾讯直连和 akshare 回退都在此完成代码映射、字段/单位标准化与上游错误封装；`Fetcher` 只负责缓存、增量水位、来源切换和观测，service、router 与 workflow 不判断具体来源。

研究模式默认路由为 `tencent → akshare`，可用 `ZHANFA_DAILY_PROVIDER` 反转主源或用 `ZHANFA_DAILY_FALLBACK_ENABLED` 禁用回退。腾讯直连包含连接/读取超时、指数退避与抖动、最大重试、每实例有界信号量和连续失败熔断。批量刷新按 50 只分批、默认最多 4 并发，单次工作流硬上限 500 只，逐只缓存即断点。

`Store` 为日线 parquet 保存同名 `.meta.json`，记录 Provider、复权方式、更新时间、请求与重试次数。TTL 过期时从缓存水位前 7 天增量拉取；前复权每 30 天同源全量校准。复权方式或来源不一致时全量覆盖，避免跨来源片段拼接。parquet 与元数据均先写同目录临时文件，再用原子替换发布。

腾讯直连只对默认的本地非商业研究用途开启。商业、公开或生产模式必须完成授权评估并显式设置风险接受；这是架构门禁，不是普通运行告警。分钟线、股票列表、指数/行业成分和财务能力仍由现有 akshare/Sina 路径提供。

## 技术选型理由

### 前端：React + TypeScript + Vite

| 考量点       | 选择                                                       | 理由                                                             |
| ------------ | ---------------------------------------------------------- | ---------------------------------------------------------------- |
| 框架         | React 18                                                   | 生态最丰富，社区最大，金融图表库支持最好                         |
| 语言         | TypeScript                                                 | 金融数据模型需要类型安全                                         |
| 图表 - K 线  | [TradingView Lightweight Charts](https://github.com/tradingview/lightweight-charts) | 专为金融 OHLCV 设计，支持伸缩/十字光标/指标叠加，Canvas 渲染性能好 |
| 图表 - 财报  | [ECharts](https://echarts.apache.org/)                     | 交互式图表种类多（柱状/折线/雷达/热力），中文本地化好            |
| UI 组件      | [shadcn/ui](https://ui.shadcn.com/) + Tailwind CSS         | 轻量、可定制、不锁 vendor                                       |
| 状态管理     | Zustand / TanStack Query                                   | 轻量，服务端状态缓存内置                                         |
| 构建工具     | Vite                                                       | 开发体验快，ESM 原生                                              |
| 路由         | TanStack Router                                            | TypeScript 类型安全路由                                          |

### 前端可靠性约定

- `App.tsx` 使用顶层 `ErrorBoundary` 包裹路由；K 线、指标副图、回测净值曲线等图表区域单独包裹错误边界，避免单个图表渲染失败拖垮整页。
- React Query 查询函数必须传递框架提供的 `AbortSignal` 到 `src/api/client.ts`，组件卸载或查询切换时取消未完成请求；手动发起的页面级请求使用 `AbortController`。
- 当前 `/api/backtest/run` 契约是单标的 `code`，前端 `BacktestForm` 使用单选标的。若后端未来支持组合回测，再把 UI 和 hook 类型恢复为多标的提交。

### 后端：FastAPI + Pydantic v2

保持 Python 技术栈一致，复用现有 `src/zhanfa/` 模块：

- **FastAPI**：异步支持、自动 OpenAPI 文档、Pydantic v2 集成
- **SQLAlchemy 2.0**：ORM，支持 SQLite（开发）和 PostgreSQL（生产）
- **Alembic**：数据库迁移
- **Celery / ARQ**：异步回测任务（回测耗时较长，不能阻塞 HTTP）

## 数据模型概要

```
strategies (流派)
  id, name, category (trend/momentum/fundamental/composite),
  description (Markdown), params (JSON: type/default/description),
  code_ref, created_at, updated_at

stocks (股票元信息)
  code, name, exchange, industry, market_cap, listed_date,
  is_active, updated_at

stock_daily (K 线 — 保留 parquet)
  code, date, open, high, low, close, volume, amount, turnover

stock_financial (财报)
  code, report_date, net_profit, revenue, eps, roe,
  debt_ratio, current_ratio, gross_margin, net_margin,
  dividend_yield, pe, pb

watchlists (自选股)
  id, name, created_at

watchlist_items
  id, watchlist_id, code, added_at, notes

backtest_results
  id, strategy_id, stock_codes (JSON), params (JSON),
  start_date, end_date, metrics (JSON), report_md, status, created_at
```

> **注意**：用户系统 (users) 暂未实现，为后续迭代预留。当前无多用户隔离，所有自选股和回测数据在单一命名空间下。

### 数据初始化约定

`stocks` 是自选股和财报数据的外键根表，不能依赖用户手工导入后才可用。数据管理的初始化接口会通过 `Fetcher.stock_list()` 缓存全 A 股列表并导入 `stocks`；日线刷新在 `discover_new=true` 时也会把同一份股票列表同步入库。自选股添加链路仍保留防御性兜底：当用户添加的代码在 `stocks` 表中不存在时，服务层会创建最小 `Stock` 记录后再写入 `watchlist_items`，避免空库环境出现外键错误。

## 部署基础设施

### CI/CD (GitHub Actions)

`.github/workflows/ci.yml` 在每次 push/PR 自动运行：
- **后端**：ruff lint → mypy 类型检查 → pytest
- **前端**：eslint → vitest → build

### Docker 部署

`docker-compose.yml` 定义三服务架构：
- **backend** — FastAPI + uvicorn (port 8000)，Dockerfile 基于 `python:3.11-slim` + uv
- **frontend** — nginx 静态文件 (port 80)，多阶段构建，API 反向代理到 backend
- **db** — PostgreSQL 16 (port 5432)，data volume 持久化

### 代码质量

pre-commit hooks (`.pre-commit-config.yaml`)：ruff (lint + format)、prettier (前端格式化)

## 后端对现有代码的复用

- `src/zhanfa/data/fetcher.py` — API 层直接 import，提供数据给前端
- `src/zhanfa/data/store.py` — parquet 缓存继续使用，K 线不存数据库（条数太大）
- `src/zhanfa/strategies/` — 策略注册表，前端列出可用策略时动态发现
- `src/zhanfa/backtest/engine.py` + `metrics.py` — 回测 API 直接调用
- `src/zhanfa/config.py` — 配置统一由后端加载，覆盖为环境变量

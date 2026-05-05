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
│  └── akshare API           ← 外部数据源                  │
└─────────────────────────────────────────────────────────┘
```

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

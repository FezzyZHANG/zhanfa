# zhanfa — 自动化投资交易辅助系统

面向 A 股研究的数据获取、策略回测与可视化平台，覆盖行情缓存、策略管理、自选股、回测分析和自动化更新。

当前策略研究默认关注 2018 年及以后的数据。个股和指数日线在本地非商业研究模式下默认使用腾讯 Provider，并保留 akshare 回退；分钟线、股票列表、指数成分和财务数据继续使用现有来源。切换到商业、公开或生产用途前，请先确认数据授权边界。

## 技术栈

Python 3.11+ · [uv](https://github.com/astral-sh/uv) · FastAPI · SQLAlchemy · pandas · vectorbt · 腾讯/akshare · React 19 · TypeScript · Vite · Tailwind CSS · TanStack Router · Playwright

## 快速开始

### 1. 准备环境

本地开发需要：

- Python 3.11 或更高版本；
- [uv](https://docs.astral.sh/uv/getting-started/installation/)；
- Node.js 22.18.0 或更高版本（与 CI 一致）；
- Git。

```bash
git clone https://github.com/FezzyZHANG/zhanfa.git
cd zhanfa

# 安装 Python 与前端依赖
uv sync --dev
uv run python -c "from pathlib import Path; Path('data').mkdir(exist_ok=True)"
cd frontend
npm ci
cd ..
```

### 2. 启动本地开发环境

后端和前端需要在两个终端中分别运行。

终端 A — 启动 FastAPI：

```bash
uv run uvicorn zhanfa.api:app --reload --host 127.0.0.1 --port 8000
```

终端 B — 启动 Vite：

```bash
cd frontend
npm run dev
```

启动后可访问：

- Web 界面：<http://localhost:5173>
- 数据初始化：<http://localhost:5173/data>
- Swagger API 文档：<http://127.0.0.1:8000/docs>
- 健康检查：<http://127.0.0.1:8000/api/health>

Vite 会把 `/api` 请求代理到本地 8000 端口。首次使用请打开“数据管理”页面执行初始化；该步骤会访问真实股票列表数据源，并将数据写入本地 SQLite 与 `data/` 缓存。

### 3. 运行研究脚本

```bash
# 获取沪深 300 成分列表，并缓存前 5 只成分股的日线示例
uv run python scripts/fetch_data.py

# 对沪深 300 指数运行双均线回测；也可追加其他指数代码
uv run python scripts/run_backtest.py

# 打开多策略研究笔记本
uv run jupyter lab notebooks/01_quickstart.ipynb
```

真实数据请求受网络、交易日和 Provider 限速影响。数据源、代理、QPS 和缓存环境变量见 [环境变量说明](developer/environment.md)。

### Docker 一键启动

已安装 Docker Compose 时，可直接启动前端、后端和 PostgreSQL：

```bash
docker compose up --build -d
docker compose ps
```

Web 界面位于 <http://localhost>，API 文档位于 <http://localhost:8000/docs>。停止服务使用 `docker compose down`；只有明确要删除数据库和缓存卷时才追加 `-v`。

## 验证

```bash
# 后端
uv run ruff check src/
uv run mypy src/
uv run pytest -v

# 前端
cd frontend
npm run lint
npm run test
npm run build
npm run contract:check
```

浏览器 E2E 的安装与运行方式见 [测试指南](developer/testing.md)。

## 项目结构

```text
src/zhanfa/
├── api/          FastAPI 路由、模型与服务
├── db/           SQLAlchemy 模型、迁移与数据导入
├── data/         数据 Provider、清洗与 parquet 缓存
├── strategies/   趋势、动量、基本面与组合策略
├── backtest/     vectorbt 回测引擎封装
├── jq/           JoinQuant 适配层
└── automation/   定时调度与数据工作流

frontend/         React 19 + TypeScript + Vite 前端及 Playwright 场景
contracts/        固定 OpenAPI 契约
scripts/          数据、回测、契约等命令行入口
notebooks/        Jupyter 研究笔记本
docs/             用户与使用文档
developer/        开发者文档、测试规范与工单
tests/            Python 测试套件
```

## 文档

- [文档入口](docs/index.md)：架构、数据管线、策略编写、回测与前端使用。
- [测试指南](developer/testing.md)：本地验证、CI 契约与浏览器 E2E。
- [开发者入口](developer/README.md)：架构决策与工单状态。
- [环境变量](developer/environment.md)：数据源、缓存、数据库和部署配置。

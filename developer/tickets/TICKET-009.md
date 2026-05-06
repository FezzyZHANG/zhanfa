# TICKET-009: 部署与 CI/CD

**优先级:** P2 - 中
**状态:** ✅ 已完成
**依赖:** 001, 002
**预计工时:** 2d

## 需求描述

为前后端项目建立开发工作流和部署方案，确保开发体验顺畅、代码质量可控、部署简单可靠。

## 开发环境

### 一键启动

```bash
# 后端 (含自动重载)
uv run uvicorn zhanfa.api:app --reload --host 0.0.0.0 --port 8000

# 前端 (含 HMR)
cd frontend && npm run dev  # → http://localhost:5173
```

### 环境变量 (`.env`)

```
# 数据库
DATABASE_URL=sqlite:///data/zhanfa.db   # 开发
# DATABASE_URL=postgresql://...         # 生产

# API
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:5173

# akshare 缓存
DATA_DIR=data
```

## 代码质量

| 工具            | 用途         |
| --------------- | ------------ |
| ruff            | Python lint + format |
| mypy            | Python 类型检查 |
| pytest          | 单元测试     |
| prettier        | 前端格式化   |
| eslint          | 前端 lint    |
| vitest          | 前端测试     |

### pre-commit hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-prettier
    hooks:
      - id: prettier
```

## CI (GitHub Actions)

```yaml
name: CI
on: [push, pull_request]

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v2
      - run: uv sync --dev
      - run: uv run ruff check src/
      - run: uv run mypy src/
      - run: uv run pytest -v

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: cd frontend && npm ci
      - run: cd frontend && npm run lint
      - run: cd frontend && npm run test
      - run: cd frontend && npm run build
```

## 部署方案

### 方案 A：单机部署（推荐起步）

```
Docker Compose:
  ├── backend   (FastAPI + uvicorn, port 8000)
  ├── frontend  (nginx 静态文件, port 80)
  └── db        (PostgreSQL, port 5432)
```

前端 `npm run build` 产出静态文件，nginx 直接 serve。API 请求通过 nginx reverse proxy 转发到 backend。

### 方案 B：轻量部署（无需 Docker）

```bash
# 后端
uv run uvicorn zhanfa.api:app --host 0.0.0.0 --port 8000

# 前端 → 构建后 serve
cd frontend && npm run build
# 用 nginx / caddy / python -m http.server 服务 dist/
```

### Dockerfile 概要

```dockerfile
# 后端
FROM python:3.11-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev
COPY src/ src/
CMD ["uv", "run", "uvicorn", "zhanfa.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 验收标准

- [x] `uv run uvicorn` + `npm run dev` 同时启动可正常工作
- [x] pre-commit hooks 配置完成
- [x] GitHub Actions CI 通过
- [x] Docker Compose `docker compose up` 一键部署
- [x] 前端请求正确代理到后端（无 CORS 错误）

## 完成记录

**完成日期:** 2026-05-05

### 新增文件
- `.pre-commit-config.yaml` — ruff + prettier hooks
- `.github/workflows/ci.yml` — 后端 (ruff/mypy/pytest) + 前端 (eslint/vitest/build)
- `Dockerfile` — 后端容器 (python:3.11-slim + uv)
- `Dockerfile.frontend` — 前端多阶段构建 (node build → nginx serve)
- `nginx.conf` — 前端静态文件 + `/api` 反向代理
- `docker-compose.yml` — 三服务编排 (backend + frontend + db)
- `frontend/vitest.config.ts` — vitest 配置 (jsdom + globals)

### 修改文件
- `.env` — 数据库/API/CORS/数据目录环境变量
- `pyproject.toml` — 新增 ruff、mypy、pre-commit 到 dev 依赖
- `frontend/package.json` — 新增 test 脚本、vitest、jsdom、prettier 依赖
- `src/zhanfa/api/__init__.py` — CORS 中间件，从环境变量读取允许来源
- `src/zhanfa/config.py` — data_dir/database_url 从环境变量读取
- `developer/README.md` — TICKET-009 状态更新
- `developer/architecture.md` — 新增部署基础设施章节
- `docs/architecture.md` — 新增部署章节（开发环境/CI/CD/Docker/代码质量）
- `docs/index.md` — 新增部署命令，快速开始增加前端启动

## 备注

- 初期优先方案 B（轻量部署），团队规模增长后再容器化
- 数据目录 `data/` 需挂载 volume 或宿主机目录，不随容器销毁
- akshare 个别接口需要网络访问，容器内确保 DNS 正常

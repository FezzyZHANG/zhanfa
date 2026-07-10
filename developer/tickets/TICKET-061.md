# TICKET-061: 代码审查 基础设施修复

> 来源：2026-05-07 全量代码审查 | 优先级：P0

## 关联文档

- [审查报告](../auto-code-review/report_full_20260507.md)

## 任务清单

### C6 — Alembic 迁移文件被 gitignore (Critical)
- [ ] `.gitignore`: 删除 `alembic/versions/` 行
- [ ] `git add alembic/versions/a1b2c3d4e5f6_add_backtest_task_id.py`
- [ ] 验证 `git status` 显示该文件被跟踪

### H4 — Dockerfile 构建失败 (High)
- [ ] `Dockerfile:5-6`: 修改 `uv sync` 分两步执行
  ```dockerfile
  COPY pyproject.toml uv.lock ./
  RUN uv sync --no-dev --no-install-project
  COPY src/ src/
  RUN uv sync --no-dev
  ```
- [ ] `Dockerfile:2`: 固定 uv 版本 `ghcr.io/astral-sh/uv:0.6.x` 替代 `:latest`
- [ ] 创建 `.dockerignore`：排除 `.venv`, `node_modules`, `__pycache__`, `*.db`, `*.parquet`

### H5 — vitest v2 与 vite v8 不兼容 (High)
- [ ] `frontend/package.json`: 升级 `"vitest": "^3.0.0"` 以匹配 Vite v8
- [ ] `npm install` 后运行 `npm run test` 验证所有测试通过

### H6 — TypeScript 未启用 strict (High)
- [ ] `frontend/tsconfig.app.json`: 添加 `"strict": true`
- [ ] 修复 strict 模式启用的类型错误
- [ ] 运行 `npm run lint` 和 `npm run build` 验证

### H8 — 数据库凭据硬编码 (High)
- [ ] `docker-compose.yml:37-39`: 改为 `POSTGRES_USER: ${POSTGRES_USER:-zhanfa}` / `POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-zhanfa}`
- [ ] 检查 `.env` 是否已在 `.gitignore` 中

### M — Alembic env.py 不从 env var 读取 DATABASE_URL
- [ ] `alembic/env.py`: 添加 `DATABASE_URL` 优先级读取逻辑

### M — pre-commit mypy + eslint 设为自动阶段
- [ ] `.pre-commit-config.yaml:17-28`: 删除 `stages: [manual]` 使 mypy 和 frontend-lint 自动执行

## 状态

待开始

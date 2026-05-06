# TICKET-056: pre-commit 补齐本地类型与前端质量门禁

**优先级:** P4 - 低
**状态:** 🔨 进行中
**依赖:** -
**预计工时:** 0.5d

## 症状

`.pre-commit-config.yaml` 当前只包含：

- ruff
- ruff-format
- prettier

CI 会运行 `mypy`、前端 lint/test/build，但本地提交前不会提前拦截 Python 类型错误或前端 lint 问题。

2026-05-07 复查补充：GitHub CI workflow fail 反复修不好时，问题不只在 pre-commit hook 缺失，也在开发者规范没有要求“按 `.github/workflows/ci.yml` 的同一命令顺序本地复现”。例如前端规范强调 `npm run test` 和 `npm run build`，但没有把 `npm run lint` 明确为交付必跑；后端规范也没有把 `uv run mypy src/` 与 `uv run pytest -v` 明确为 CI 修复收尾门禁。

## 根因分析

本地 pre-commit 与 CI 质量门禁不完全一致，开发者可能到 push/PR 后才发现类型或前端 lint 失败。对于当前已有较完整测试矩阵的项目，pre-commit 可以承担更早的反馈。

## 修复方案

### 1. 增加 mypy hook

评估直接使用本地 `uv run mypy src/` 的 local hook，避免 pre-commit 单独安装依赖导致环境不一致。

### 2. 增加前端 lint hook

使用 local hook：

```bash
cd frontend && npm run lint
```

可按文件过滤或作为 manual stage，避免每次提交过慢。

本工单选择 manual stage：

- `pre-commit run mypy --all-files --hook-stage manual`
- `pre-commit run frontend-lint --all-files --hook-stage manual`

原因：`mypy` 与前端 lint 都是全项目检查，放入默认 commit stage 会明显拖慢纯文档或小改提交；manual stage 保留本地一键复现能力，并与 CI 修复流程配套。

### 3. 文档说明

更新 `developer/testing.md` 或环境文档，说明本地 pre-commit 与完整 CI 的关系。

### 4. CI 修复流程对齐

在 `developer/testing.md` 和工程中台规范中明确：

- 修复 GitHub Actions 失败前必须读取 `.github/workflows/ci.yml`
- 本地按失败 job 的同一命令顺序复现与验证
- 前端 CI 修复必须包含 `npm run lint`、`npm run test`、`npm run build`
- 后端 CI 修复必须包含 `uv run ruff check src/`、`uv run mypy src/`、`uv run pytest -v`

## 验收标准

- [ ] pre-commit 能在本地运行 Python 类型检查或明确提供 manual stage
- [ ] pre-commit 能运行前端 lint 或明确提供 manual stage
- [ ] 不显著拖慢普通文档/小改提交
- [x] 开发者规范明确 CI 修复必须复刻 `.github/workflows/ci.yml` 的失败 job 命令
- [x] 前端开发规范明确 `npm run lint` 不能被 `npm run build` 替代
- [x] 后端开发规范明确 `ruff`、`mypy`、`pytest -v` 都属于 CI 修复收尾门禁
- [ ] `pre-commit run --all-files` 可通过

## 验证记录

- 待补充

## 来源

- `developer/auto-code-review/report_full_20260506.md` — 6.3 Pre-commit、P4 路线图第 13 项

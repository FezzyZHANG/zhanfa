# 标准测试流程

本文档描述开发工单的推荐验证路径。目标不是每次都机械跑满所有命令，而是用最小但足够的测试覆盖本次改动风险，并在交付说明中明确已经验证和未验证的部分。

## 基本原则

1. 先跑与改动最接近的测试，再跑全量回归。
2. 后端涉及数据库、API、回测、数据缓存时，至少覆盖对应 service 测试和 API 测试。
3. 前端涉及类型、API client、页面、图表组件时，至少跑 ESLint、Vitest 和生产构建。
4. 对 akshare、文件缓存、数据库等外部状态敏感逻辑，测试必须使用 mock、临时目录或隔离数据库，不直接依赖本地 `data/zhanfa.db`。
5. 如果某个检查失败但与本工单无关，不顺手大改；在交付说明里标注为既有问题，并视情况新建工单。
6. 修复 GitHub Actions 失败时，本地必须按 `.github/workflows/ci.yml` 的同一命令顺序复现并验证；只跑相似命令不算 CI 修复完成。

## 持续维护基线

[TICKET-066](tickets/TICKET-066.md) 持续跟踪关键用户场景测试、跨端契约和 CI 场景管线，不以一次性 `✅ 已完成` 关闭。其状态使用 `🔁 持续维护（vNNN）`：`NNN` 取最近一次完成滚动检查时已纳入检查的最高工单编号。

当前基线为 `v066`。新增更高编号工单不会自动推进版本；只有复核新工单对前端、API、workflow、存储和外部 Provider 边界的影响，并执行当时已落地的契约及用户旅程测试后，才能同步推进 `TICKET-066` 和工单总览中的版本。

用户场景测试遵循以下边界：

- 浏览器 E2E 保留真实 React、真实 HTTP API、真实 workflow 和隔离存储。
- 只 mock 或替换腾讯、AKShare 等不可控外部服务，不 mock 正在验证的 `/api` 边界。
- 普通 PR 使用确定性 Fixture Provider；真实 Provider 调用进入独立的定时探针。
- 跨模块缺陷优先在可稳定复现的最低测试层补回归；仅当风险贯穿关键用户旅程时增加浏览器 E2E。

## CI 对齐命令

GitHub Actions 当前执行以下门禁。CI 失败工单完成前必须在本地至少跑失败 job 对应的完整命令；若改动跨前后端，则两组都跑。

```bash
# backend job
uv sync --dev
uv run ruff check src/
uv run mypy src/
uv run pytest -v

# frontend job
cd frontend
npm ci
npm run lint
npm run test
npm run build
```

注意：

- `uv run pytest -q` 适合日常全量回归，但 CI 修复收尾必须跑 `uv run pytest -v`，避免输出、收集和插件行为差异被漏掉。
- `npm run build` 会覆盖 TypeScript 编译和 Vite 构建，但不能替代 `npm run lint`。
- 不要用已有的 `node_modules/` 或未同步的虚拟环境判断 CI 是否会绿；CI 从干净依赖安装开始。

## 本地 Pre-commit

普通提交默认运行轻量检查：

```bash
uv run pre-commit run --all-files
```

Python 格式化、`mypy` 和前端 lint 作为 manual hook 提供，避免每次文档或小改提交都触发较慢的全项目检查。修复 CI、类型、前端 lint 或跨端契约问题时显式执行：

```bash
uv run pre-commit run mypy --all-files --hook-stage manual
uv run pre-commit run frontend-lint --all-files --hook-stage manual
```

如需格式化本次改动的 Python 文件，可按文件运行：

```bash
uv run pre-commit run ruff-format --files src/zhanfa/<module>.py --hook-stage manual
```

manual hook 复用本地项目环境：`mypy` 使用 `uv run mypy src/`，前端 lint 使用 `frontend` 目录下的 `npm run lint`。如果这些命令失败，先按 CI 失败处理流程定位，不要只跳过 hook。

## 快速判定矩阵

| 改动范围 | 先跑 | 完成前再跑 |
|----------|------|------------|
| 纯文档 | 不必跑自动化测试；检查链接和命令准确性 | 可选 `git diff --check` |
| Python 单元逻辑 | `uv run pytest tests/<相关目录> -q` | `uv run ruff check src/` + `uv run mypy src/` + `uv run pytest -v` |
| 后端 API / service | 相关 service + `tests/test_api` | `uv run ruff check src/` + `uv run mypy src/` + `uv run pytest -v` |
| 数据库 / ORM / 初始化 | `tests/test_db` + 相关 API/service 测试 | backend CI 对齐命令 |
| 回测引擎 / 指标 | `uv run pytest tests/test_backtest -q` | backend CI 对齐命令 |
| 前端 API client / hooks | `cd frontend && npm run test` | `npm run lint` + `npm run test` + `npm run build` |
| 前端页面 / 图表 | `cd frontend && npm run test` | `npm run lint` + `npm run test` + `npm run build`，必要时浏览器手验 |
| 前后端契约 | 后端相关 API 测试 + 前端 client 测试 | backend + frontend CI 对齐命令 |

## 后端流程

### 1. 定向测试

根据改动文件选择最小测试集，例如：

```bash
uv run pytest tests/test_services/test_watchlist_service.py -q
uv run pytest tests/test_api/test_data.py -q
uv run pytest tests/test_backtest/test_engine.py -q
```

修复 bug 时优先补一个会在旧实现下失败的回归测试，再改实现。

### 2. 全量测试

交付后端代码前默认执行：

```bash
uv run pytest -q
```

当前测试体系会为 API 测试设置隔离 SQLite 数据库。不要在测试里直接读写默认开发库 `data/zhanfa.db`。

### 3. 质量检查

CI 当前执行：

```bash
uv run ruff check src/
uv run mypy src/
```

本地开发时，建议先对本工单涉及文件跑 ruff：

```bash
uv run ruff check src/zhanfa/<module>.py tests/<相关测试>.py
```

全量 `uv run ruff check src tests` 可作为额外检查，但如果暴露历史旧账，需在交付说明中区分“本工单范围内已通过”和“项目既有问题”。

## 前端流程

### 0. Lint

涉及前端代码时先执行：

```bash
cd frontend
npm run lint
```

`npm run build` 不能替代 lint。React Hooks、refs、组件定义位置、未使用变量等问题经常只在 ESLint 中暴露，也是 GitHub Actions 的独立失败点。

### 1. 测试

涉及 API client、hooks、组件、页面时执行：

```bash
cd frontend
npm run test
```

新增 UI 行为时优先补组件测试或页面测试；图表类组件至少保证 mock 覆盖不会因库 API 变化而静默失效。

### 2. 构建

前端交付前默认执行：

```bash
cd frontend
npm run build
```

`npm run build` 同时覆盖 TypeScript 编译和 Vite 生产构建。若只想快速看类型问题，可运行：

```bash
cd frontend
npx tsc -p tsconfig.app.json --noEmit
```

### 3. 浏览器手验

以下改动建议打开浏览器手验：

- K 线、净值曲线、回撤曲线等 Canvas/图表组件
- 表单提交流程，例如添加自选股、提交回测、数据刷新
- 响应式布局、弹窗、菜单、批量操作

手验时至少确认页面无控制台错误、关键按钮可点击、加载/错误/空状态合理。

## 数据与外部依赖

### akshare

单元测试不要真实调用 akshare。使用 `unittest.mock.patch` 替换 `Fetcher` 或 akshare 函数，构造稳定 DataFrame。

真实 akshare 调用仅用于人工联调，且结果可能受网络、交易日、接口限流影响。若联调失败，先确认是代码问题还是数据源问题，再决定是否写入 `developer/debug-notes.md`。

### parquet 缓存

涉及 `Store` 的测试使用 `tempfile.TemporaryDirectory()` 创建临时数据目录。不要依赖当前工作区已有的 `data/` 内容。

### 数据库

API 测试必须使用隔离数据库；service 层测试可使用 fixture 创建内存 SQLite。涉及线程池或异步后台任务时，不要使用普通 `sqlite:///:memory:` 作为跨线程共享库，优先使用临时文件 SQLite 或 `StaticPool`。

## 交付前检查清单

提交工单前，在最终说明中列出实际执行过的命令和结果：

- [ ] 已补或更新相关测试
- [ ] 相关定向测试通过
- [ ] 后端改动已跑 `uv run ruff check src/`、`uv run mypy src/` 和 `uv run pytest -v`
- [ ] 前端改动已跑 `npm run lint`、`npm run test` 和 `npm run build`
- [ ] CI 失败修复已按 `.github/workflows/ci.yml` 复刻失败 job 的完整命令
- [ ] 需要手验的 UI/API 流程已手验，或已说明未手验
- [ ] 已同步相关 `docs/`、`developer/` 文档

## 常用命令汇总

```bash
# 后端
uv run pytest -q
uv run pytest tests/test_api -q
uv run pytest tests/test_services/test_watchlist_service.py -q
uv run ruff check src/
uv run mypy src/

# 前端
cd frontend
npm run test
npm run build
npm run lint
npx tsc -p tsconfig.app.json --noEmit
```

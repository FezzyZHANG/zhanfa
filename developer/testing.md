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

[TICKET-067](tickets/TICKET-067.md) 负责一次性建设 Playwright、隔离前后端运行时、OpenAPI 契约门禁和 CI 诊断产物；框架完成后关闭 `TICKET-067`，后续场景维护仍回到 `TICKET-066`。

当前基线为 `v067`。新增更高编号工单不会自动推进版本；只有复核新工单对前端、API、workflow、存储和外部 Provider 边界的影响，并执行当时已落地的契约及用户旅程测试后，才能同步推进 `TICKET-066` 和工单总览中的版本。

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

# contract-e2e job（依赖 backend + frontend job）
uv sync --dev
cd frontend
npm ci
npm run contract:check
npx playwright install --with-deps chromium
npm run test:e2e
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

## 跨端契约与浏览器 E2E

`TICKET-067` 提供统一的 OpenAPI 漂移门禁与 Playwright 隔离运行时。生成工具要求 Node.js `22.18.0+`；CI 固定使用 `22.18.0`。首次本地运行先安装依赖和 Chromium：

```bash
cd frontend
npm ci
npx playwright install chromium
```

### OpenAPI 契约

```bash
# 只验证；普通 PR 和 CI 使用，不改文件
npm run contract:check

# 仅在后端契约有意变化时更新固定 schema 和生成类型
npm run contract:generate
```

`contract:check` 先直接调用 FastAPI `app.openapi()` 与 `contracts/openapi.json` 比较，再将 `@hey-api/openapi-ts@0.99.0` 的结果生成到临时目录，与 `frontend/src/api/generated/` 比较。数据管理 API client 使用的 `DataStats`、`StockDataStatus`、`RefreshRequest` 和 `RefreshResult` 均引用这些生成类型，不是旁路产物。`tests/test_contract/test_openapi_export.py` 会故意删除响应字段，验证漂移检查确实失败。

### Playwright 场景

```bash
cd frontend
npm run test:e2e                 # 普通稳定门禁，默认排除 @live
npm run test:e2e:smoke           # 只跑 @smoke
npm run test:e2e:scenario        # 只跑 @scenario；当前包含数据管理成功主旅程
npm run test:e2e:live            # 显式运行真实 Provider 探针，不进入普通 PR

# 单文件、标题和本地调试
npm run test:e2e -- e2e/smoke/data-lifecycle.spec.ts
npm run test:e2e -- --grep "data lifecycle"
npm run test:e2e -- --headed
npm run test:e2e -- --debug
```

`run-e2e.mjs` 每次分配随机端口和独立临时目录，设置临时 SQLite、`DATA_DIR`、Fixture 股票列表与 Daily Provider，并关闭 scheduler；Playwright 配置等待后端 `/api/health` 和 Vite URL，始终只使用一个 Chromium worker。外层启动器在成功、失败或受控中断后清理运行目录，并比较运行前后的工作区 `data/` 快照。普通测试不得 `page.route()` 拦截 `/api`；共享 fixture 会把浏览器 console error、page error、站内 API 5xx 和公网请求转成失败。

当前 `data-lifecycle.spec.ts` 同时标记 `@smoke @scenario`，从空状态真实调用初始化与刷新接口，经过 workflow 写入临时 parquet，断言 Fixture Provider、统计更新和页面重载后的持久状态。初始化必须让 `import_stocks()` 复用 `Fetcher.store`；若改回默认 `data/`，该场景会读到工作区股票列表并因隔离数据数量漂移而失败。

默认会启动全新服务。仅在已手工启动的服务本身也使用隔离 E2E 环境时，才可设置 `E2E_REUSE_SERVERS=true` 并通过 `E2E_BACKEND_PORT` / `E2E_FRONTEND_PORT` 指定端口。

`test:e2e:live` 不注入 Fixture Daily Provider，默认使用腾讯；可通过 `ZHANFA_LIVE_DAILY_PROVIDER` 显式选择真实 Provider。live 仍使用临时数据库和缓存，但会访问公网，只能放入独立定时探针，不能加入普通 PR job。

报告与诊断文件位于 `frontend/e2e-artifacts/`：

- `html-report/`：Playwright HTML 报告；
- `test-results/`：失败截图、error context 和 `retain-on-failure` trace；
- `logs/backend.log`、`frontend.log`、`playwright.log`：两个服务和测试进程日志；
- `logs/runtime.json`：本次临时路径与端口，仅用于定位，数据目录本身在退出时删除。

CI 的 `contract-e2e` job 显式依赖 backend/frontend job，总超时 20 分钟；失败或取消时上传上述目录 7 天，成功不上传 trace 和大体积报告。

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
npm run contract:check
npm run test:e2e:smoke
```

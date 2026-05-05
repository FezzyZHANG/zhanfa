# 标准测试流程

本文档描述开发工单的推荐验证路径。目标不是每次都机械跑满所有命令，而是用最小但足够的测试覆盖本次改动风险，并在交付说明中明确已经验证和未验证的部分。

## 基本原则

1. 先跑与改动最接近的测试，再跑全量回归。
2. 后端涉及数据库、API、回测、数据缓存时，至少覆盖对应 service 测试和 API 测试。
3. 前端涉及类型、API client、页面、图表组件时，至少跑 TypeScript 构建和 Vitest。
4. 对 akshare、文件缓存、数据库等外部状态敏感逻辑，测试必须使用 mock、临时目录或隔离数据库，不直接依赖本地 `data/zhanfa.db`。
5. 如果某个检查失败但与本工单无关，不顺手大改；在交付说明里标注为既有问题，并视情况新建工单。

## 快速判定矩阵

| 改动范围 | 先跑 | 完成前再跑 |
|----------|------|------------|
| 纯文档 | 不必跑自动化测试；检查链接和命令准确性 | 可选 `git diff --check` |
| Python 单元逻辑 | `uv run pytest tests/<相关目录> -q` | `uv run pytest -q` |
| 后端 API / service | 相关 service + `tests/test_api` | `uv run pytest -q` |
| 数据库 / ORM / 初始化 | `tests/test_db` + 相关 API/service 测试 | `uv run pytest -q` |
| 回测引擎 / 指标 | `uv run pytest tests/test_backtest -q` | `uv run pytest -q` |
| 前端 API client / hooks | `cd frontend && npm run test` | `cd frontend && npm run build` |
| 前端页面 / 图表 | `cd frontend && npm run test` | `cd frontend && npm run build`，必要时浏览器手验 |
| 前后端契约 | 后端相关 API 测试 + 前端 client 测试 | 后端全量 + 前端 build/test |

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
- [ ] 后端改动已跑 `uv run pytest -q`
- [ ] 前端改动已跑 `npm run test` 和 `npm run build`
- [ ] 本工单相关 ruff/typecheck 通过，或已说明既有失败项
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

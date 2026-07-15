# TICKET-067: 跨端用户场景测试框架与契约门禁

- **优先级:** P1 - 高
- **状态:** 📋 待开始
- **依赖:** 066, 009, 032
- **预计工时:** 3-5d

## 背景

[TICKET-066](TICKET-066.md) 已将关键用户场景与跨端契约定义为持续维护的质量基线，但当前仓库还缺少承载这些检查的统一框架：

- 前端 Vitest 页面测试通常 mock hook 或 API client，不能发现真实 HTTP 契约漂移。
- 后端 API 生命周期测试不启动真实浏览器和前端构建。
- CI 没有同时启动隔离后端、真实前端和浏览器的 job。
- FastAPI 已提供 OpenAPI schema，但前端 TypeScript 类型仍主要手工维护。
- 外部 Provider、开发数据库和本地 parquet 必须与稳定测试隔离，否则场景测试会慢、脆弱且不可重复。

本工单负责一次性建设可复用的测试框架。框架交付后可以标记完成；具体业务旅程、回归场景和检查版本仍由 `TICKET-066` 长期滚动维护。

## 目标架构

```text
Playwright 浏览器
        │ 用户可见操作
        ▼
真实 React / Vite ──真实 HTTP──> 隔离 FastAPI 进程
                                      │
                         ┌────────────┴────────────┐
                         ▼                         ▼
                 临时 SQLite / parquet      Fixture Provider

FastAPI app.openapi() ──> 固定 OpenAPI 产物 ──> 前端类型生成/校验 ──> CI 漂移门禁
```

框架必须保留浏览器、前端、`/api`、workflow 和存储这些正在验证的边界，只替换腾讯、AKShare 等项目无法控制的外部服务。

## Critical 范围

### 1. Playwright 基础设施

- [ ] 在前端开发依赖和 lockfile 中引入 Playwright Test。
- [ ] 新增 `playwright.config.ts`，统一管理 base URL、超时、重试、trace、截图和报告目录。
- [ ] 配置前后端两个 web server 及健康检查；本地允许复用已有服务，CI 必须使用全新隔离进程。
- [ ] CI 初期只安装和运行 Chromium，`workers=1`，优先保证可重复性；多浏览器不属于本工单。
- [ ] 提供稳定命令，例如 `npm run test:e2e`，并确保从仓库约定的工作目录执行时行为明确。

### 2. 隔离的后端测试运行时

- [ ] 提供专用 E2E 启动入口或脚本，通过环境变量使用临时 SQLite、临时 parquet 目录和关闭自动 scheduler 的 app 配置。
- [ ] Fixture Provider 通过依赖注入或测试启动配置接入，不新增可在普通运行模式调用的测试后门 API。
- [ ] E2E 进程不得读写默认 `data/zhanfa.db`、工作区现有 `data/` 或用户环境中的真实缓存。
- [ ] 每个测试运行拥有独立数据目录，并在成功或失败后可靠清理；失败日志保留必要路径和上下文。
- [ ] 启动阶段等待 `/api/health` 和前端 URL 可用，超时后打印两个进程的 stderr，而不是静默挂起。

### 3. OpenAPI 契约门禁

- [ ] 从 FastAPI app 确定性导出 OpenAPI schema，避免依赖已启动的共享开发服务。
- [ ] 选择并固定 TypeScript OpenAPI 生成或校验工具版本，同时提交 lockfile 变化。
- [ ] 生成或校验前端实际使用的请求/响应类型；不得只生成一份未被 API client 引用的旁路类型文件。
- [ ] 提供 `npm run contract:check` 或等价命令；当后端 schema 与已提交前端契约漂移时返回非零退出码。
- [ ] CI 的契约检查只验证，不自动覆盖并提交生成文件。

### 4. 框架证明场景

- [ ] 至少实现一条不依赖公网的全栈 smoke：浏览器打开数据管理页，通过真实 `/api/data/stats` 读取隔离后端状态并渲染。
- [ ] 证明该场景没有拦截或 mock `/api` 请求，且后端使用临时数据库/缓存。
- [ ] 至少包含一次页面重载，确认状态来自后端而不是仅存在于前端内存。
- [ ] 断言使用 role、label、可见文本等用户可见契约，不依赖 CSS 结构或内部 React 状态。
- [ ] 捕获未处理的浏览器 console error、page error 和关键 API 5xx，并让测试失败。

### 5. CI 与诊断产物

- [ ] 在 `.github/workflows/ci.yml` 增加独立的 contract/E2E job，并明确与现有 backend、frontend job 的关系。
- [ ] CI 按 lockfile 安装依赖和 Chromium 运行时，不复用开发机 `node_modules`。
- [ ] 失败或取消时上传 Playwright HTML 报告、trace、前端日志和后端日志；成功运行不长期保存大体积 trace。
- [ ] 为 job 设置合理总超时，子进程退出异常不得让 CI 长时间悬挂。

### 6. 文档与维护交接

- [ ] 更新 `developer/testing.md`：本地命令、定向运行、调试、报告位置和 CI 对齐要求。
- [ ] 更新 `developer/debug-notes.md`：Windows 子进程、端口占用、浏览器安装和 CI 排障要点。
- [ ] 在 `TICKET-066` 中记录框架实际能力、首批可维护场景和仍未覆盖的风险。
- [ ] 完成本工单后不把所有未来 E2E 塞回本工单；新增、删减和版本检查继续归 `TICKET-066`。

## High 范围

- [ ] 提供共享 fixture：测试环境配置、种子数据、API 等待和临时目录生命周期。
- [ ] 支持 `smoke`、`scenario`、`live` 等清晰分组；`live` 不进入普通 PR 稳定门禁。
- [ ] 支持按单文件或标题定向运行，并可用 headed/debug 模式本地排障。
- [ ] 在 Windows 本地和 Linux CI 上使用同一套测试语义，平台差异集中在启动适配层。
- [ ] 增加一个故意改变 OpenAPI 字段会使契约检查失败的框架自测或可重复验证步骤。

## 非目标

- 不在本工单修复数据刷新长任务、30 秒超时或 `RefreshResult` 展示问题。
- 不在本工单补齐数据刷新、自选股、回测等全部业务旅程。
- 不让普通 PR E2E 访问真实腾讯、AKShare 或其他公网数据源。
- 不在首版建设 Firefox/WebKit 矩阵、视觉回归、性能压测或生产环境合成监控。
- 不用浏览器 E2E 替代现有 Pytest、Vitest、lint、类型检查和 API 集成测试。

## 建议交付结构

实际文件名可在实现时按工具约束微调，但职责应保持清晰：

```text
frontend/
├── playwright.config.ts
├── e2e/
│   ├── fixtures/
│   └── smoke/
└── package.json                 # test:e2e / contract:check

scripts/或tests/support/
├── export_openapi.py
└── run_e2e_backend.py           # 或等价的受控启动入口

.github/workflows/ci.yml         # contract/E2E job
```

## 验收标准

- [ ] 干净依赖环境中，契约检查命令能够稳定通过。
- [ ] 人为删除或改变一个前端正在使用的后端响应字段时，契约检查稳定失败；恢复后通过。
- [ ] `npm run test:e2e` 可自动启动前后端、运行 Chromium smoke 并自动退出，无需人工预先启动服务。
- [ ] smoke 的浏览器请求真实到达 FastAPI，数据来自隔离存储，且全过程不访问真实外部 Provider。
- [ ] 测试运行前后默认开发数据库和工作区 `data/` 不发生变化。
- [ ] CI contract/E2E job 通过；制造一次受控失败时能下载 trace 和前后端日志定位原因。
- [ ] 现有 backend 与 frontend CI 对齐命令保持通过。
- [ ] `developer/testing.md`、`developer/debug-notes.md`、`developer/README.md` 和 `TICKET-066` 与实际框架一致。

## 交付后关系

本工单完成表示“框架可用”，不表示用户场景测试建设结束。完成后：

- `TICKET-067` 标记 `✅ 已完成`，保留最终命令、验证结果和残余风险。
- `TICKET-066` 保持 `🔁 持续维护（vNNN）`，在下一次滚动检查时才根据当时最高工单号推进版本。
- 后续业务问题优先建立独立修复工单；是否补入关键用户旅程由 `TICKET-066` 维护清单决定。

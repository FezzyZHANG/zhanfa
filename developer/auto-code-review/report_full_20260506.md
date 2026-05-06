# 工程中台 · 全量代码审查报告

> 审查时间：2026-05-06 | 审查范围：全仓库 | 测试状态：295 pass (backend) + 153 pass (frontend)

---

## 一、总体印象

这是一份**有品位**的代码库。整体结构清晰、分层合理、约定一致、测试扎实。在金融量化这个“容易写出意大利面条”的领域里，项目保持了不错的克制。以下是逐层细评。

| 维度 | 评分 | 说明 |
|------|------|------|
| 架构分层 | ★★★★☆ | 后端 router→service→data 三层清晰，前端 hooks→api 隔离到位 |
| 类型安全 | ★★★☆☆ | Pydantic 侧完整，前端有断点（`as` 强制转换多） |
| 错误处理 | ★★★☆☆ | 服务层大量 try/except pass，静默吞错是隐藏炸弹 |
| 测试覆盖 | ★★★★☆ | E2E + 单元 + API 集成，前端 mock 层次设计好。缺契约测试 |
| 代码一致性 | ★★★★☆ | Python 风格统一，TS 略有参差但不大 |
| 基础设施 | ★★★★☆ | CI 双轨、Docker 三服务、pre-commit — 齐整 |
| 文档 | ★★★★☆ | docs/ + developer/ 双轨覆盖好，独缺 release checklist |

---

## 二、架构层（值得肯定）

### 2.1 后端分层：干净克制

```
router (薄) → service (逻辑) → data/fetcher + db (持久化)
```

**值得表扬的决策：**

- [backtest_service.py](src/zhanfa/api/services/backtest_service.py) 的内存 `_tasks` + DB 持久化双写模式 — 既保证了运行时速度，又保证了重启后可查。`get_task()` 的内存优先→DB 兜底策略是经典模式。
- [watchlist_service.py](src/zhanfa/api/services/watchlist_service.py) 的 `_ensure_stock()` 防御性兜底 — 外键约束 + 容错同时满足，设计意图明确。
- [fetcher.py](src/zhanfa/data/fetcher.py) 的 TTL 缓存体系 — `load(code, freq, max_age=ttl)` 的签名统一、语义清晰。env var 全部可覆盖，运维友好。
- [Strategy](src/zhanfa/strategies/base.py) 的抽象基类 — `generate_signals` 接口简洁，`position_weights` 预留了组合扩展点但不强制，符合 YAGNI。

**值得警惕的信号：**

- `__init__.py` 模块顶层直接调用 `init_db()` — 这意味着 `import zhanfa.api` 就会立即执行数据库初始化。这在生产和测试中是两类行为（测试在 conftest.py 里又做了一次 init），属于隐式副作用。建议搬到 `lifespan` 里统一管理。
- `_register_scheduler_tasks()` 同样在模块顶层启动后台线程 — 任何 `import` 都会触发，甚至在 mypy/lint 时也会跑。强烈建议改为 `lifespan` 内显式调用。

### 2.2 前端分层：hooks 抽象好

- 每个 page 对应一组 hooks（`useWatchlists`、`useData` 等），API client 函数与 mock 函数同签名同返回类型，切换 `VITE_ENABLE_MOCK=true` 即可全前端开发。
- [client.ts](frontend/src/api/client.ts) 的 USE_MOCK 分支是可开关的全链路 mock，配合 mock.ts 的假数据生成器，开发体验优秀。

**值得警惕的信号：**

- [client.ts](frontend/src/api/client.ts) 里三种后端返回格式 → `BacktestResult` 的映射函数（`historyItemToResult`、`taskToResult`、`strategyResultToBacktestResult`）有三份，每份都手写了完整的 metrics 默认值兜底逻辑。这是典型的“类型映射蔓延” — 后端已经返回了标准结构，前端不应再手写三次。建议收敛为一个 `normalizeBacktestResult(raw: unknown): BacktestResult` 函数。
- [StockInfo](frontend/src/types/index.ts) 前端类型声明了 `exchange`、`industry`、`market_cap` 等字段，但后端 `/api/stocks/{code}` 实际上只返回 `{code, name, latest_financial}` — `fetchStock()` 里用空字符串和 0 硬填充了缺失字段。这属于前后端契约不一致，建议要么后端补齐字段，要么前端类型声明为 `Partial`。

---

## 三、代码质量细项

### 3.1 静默吞错（最严重问题）

以下位置使用 `except Exception: pass` 吞掉了所有异常，且没有日志：

| 文件 | 位置 | 风险 |
|------|------|------|
| [watchlist_service.py:274](src/zhanfa/api/services/watchlist_service.py#L274) | `names` 查询 | 若 DB 挂了，自选股全部显示空名称 |
| [watchlist_service.py:325](src/zhanfa/api/services/watchlist_service.py#L325) | 每日价格 fetch | 若 akshare 超时，该股票静默显示无数据 |
| [watchlist_service.py:344](src/zhanfa/api/services/watchlist_service.py#L344) | 财务 fetch | PE/PB 全部 null 却无提示 |
| [data.py:99](src/zhanfa/api/routers/data.py#L99) | stock-status 各缓存检查 | 坏 parquet 文件被完全忽略 |
| [data.py:112](src/zhanfa/api/routers/data.py#L112) | 分钟级缓存检查 / watchlist 查询 | 同上 |

**中台建议：** 至少加 `logger.warning("获取 %s 失败", code, exc_info=True)`。尤其 `stock-status` 是用户排查“为什么没数据”的入口 — 它自己把错误藏起来，用户永远找不到原因。

### 3.2 N+1 查询（性能隐患）

[watchlist_service.py:278-358](src/zhanfa/api/services/watchlist_service.py#L278-L358) 的 `get_watchlist_quotes()` 对每个 item 独立发起 `Fetcher.daily()` 和 `Fetcher.financial()` — 如果自选股 50 只，就是 50 次 akshare 调用 × 2（行情+财务）= 100 次 HTTP。

好在 cache-first 策略兜底了大部分场景，但在 `store.last_close()` 返回 None 的 fallback 路径中，这就是实实在在的 N+1 问题。建议对 daily 做一次 `Fetcher.daily_batch(codes)` 批量拉取。

### 3.3 日期处理的双轨制

整个代码库有两种日期格式并存：
- `"20200101"` (8位无分隔符) — 来自 akshare 参数约定
- `"2020-01-01"` (ISO 8601) — JSON API 返回

[backtest_service.py:27](src/zhanfa/api/services/backtest_service.py#L27) 的 `_parse_date()` 和 [client.ts:467-468](frontend/src/api/client.ts#L467-L468) 的 `start_date.replace(/-/g, '')` 分别处理了这个转换。这种转换散布在三处，建议收拢到后端 request model 的 validator 里，前端只发 ISO 格式。

### 3.4 Config 类的半废弃

[config.py](src/zhanfa/config.py) 定义了 `update_hour: int = 17`，但实际调度注册在 `__init__.py` 里写死了 `"15:30"` 和 `"16:00"`。配置值和实际值不一致。要么让调度时间从 Config 读取，要么删掉无用字段。

### 3.5 策略注册的双轨制

[register_strategies.py](src/zhanfa/db/register_strategies.py) 将策略写入 DB，[strategy_service.py:145-164](src/zhanfa/api/services/strategy_service.py#L145-L164) 又维护了一份硬编码 `_fallback` dict。当新增策略时，两处都需要更新 — 迟早会忘掉一处。

建议：`_fallback` 改为从 `register_strategies()` 返回值动态生成，或直接从 DB 读。

---

## 四、类型安全

### 4.1 后端 Pydantic：好

[models.py](src/zhanfa/api/models.py) 的 Pydantic 模型定义完整，response_model 在几乎所有端点上都有声明。`DailyDataPoint.date: date | datetime` 这个 union 虽然不干净，但如实反映了 parquet 的 daily/minute 两种索引格式，是可接受的。

### 4.2 前端 TypeScript：有断点

以下位置使用了不安全的类型收缩：

- [client.ts:88-95](frontend/src/api/client.ts#L88-L95) — `fetchStock()` 返回类型是 `StockInfo | undefined`，但实际返回的对象用 `exchange: ''` 等硬填充字段，类型与值不符。
- [client.ts:401](frontend/src/api/client.ts#L401) — `m.ann_return ?? 0` — `Record<string, number> | null` 类型中 `m` 可能为 null，但代码假设了解构安全（在 `null` 上展开是合法的 JS 但类型检测应报警）。
- [client.ts](frontend/src/api/client.ts) 的三个映射函数中多处 `as 'buy' | 'sell'` 强制类型断言 — 如果后端返回了第三个值（如 `"hold"`），前端会在运行时静默出错。

### 4.3 MinuteCacheStatus 默认值问题

[models.py:367](src/zhanfa/api/models.py#L367) 的 `minute_60: MinuteCacheStatus = MinuteCacheStatus()` — 这在 Python 中是**类级别共享**的可变默认值！虽然 Pydantic v2 在运行时做了深拷贝防护，但这仍是反模式。应改为 `Field(default_factory=MinuteCacheStatus)`。

---

## 五、测试体系

### 5.1 后端测试架构：精巧

[conftest.py](tests/conftest.py) 的处理方式值得称道：

1. 模块顶层 `_TEST_DB_PATH` — 进程级隔离，`atexit` 清理
2. `client` fixture — 通过 monkeypatch 注入内存 SQLite，不走实际文件系统
3. [test_watchlists.py](tests/test_api/test_watchlists.py) 的 `test_watchlist_e2e_lifecycle` — 真正的端到端：create→add→quotes→notes→batch→export→delete，13 步完整用户旅程

**测试覆盖好但缺几块：**
- 无 backend 定时任务实际执行的集成测试（scheduler 单元测试有，但无 end-to-end 的 schedule→fetch→cache 链路）
- 无并发竞态测试（backtest_service 的 `_tasks` dict 在多线程下无锁保护，理论上存在竞态条件但未被测到）
- 无 parquet 文件损坏后的降级行为测试

### 5.2 前端测试架构：mock 分层好

```ts
// 三层 mock 设计：
vi.mock('axios')        // L1: HTTP 层
vi.mock('@/hooks/...')  // L2: 数据层
// 组件直接测渲染逻辑
```

[WatchlistPage.test.tsx](frontend/src/pages/watchlist/__tests__/WatchlistPage.test.tsx) 的 `makeQuoteItem()` helper 和可变模块级状态 (`mockSelectedId`) 设计得实用。mock 覆盖了 loading、empty、error、数据变化四态。

**缺口：** 无 `DataPage` 前端测试、无图表组件（Canvas）测试。图表组件在 jsdom 下确实难测，但至少应该测数据转换逻辑的纯函数。

---

## 六、基础设施

### 6.1 CI/CD

[ci.yml](.github/workflows/ci.yml) 双 Job 并行，lint→typecheck→test→build 流水线标准。有一个潜在问题：

```yaml
- run: cd frontend && npm ci
```

`cache-dependency-path: frontend/package-lock.json` 声明了但 npm cache hit 策略取决于 `package-lock.json` hash — 如果 lock 文件频繁变（常见于 monorepo），缓存命中率会很低。建议加 `cache: npm` 的时间戳兜底策略。

### 6.2 Docker

[docker-compose.yml](docker-compose.yml) 三服务架构干净：backend 有 `depends_on db (healthy)` 安全检查，db 有 healthcheck。但 frontend 的 `depends_on: backend` 缺少 healthcheck 条件 — 如果 backend 启动慢（首次 alembic migration），nginx 已经起来了但 upstream 不可用，用户在页面上会看到 502。

### 6.3 Pre-commit

`.pre-commit-config.yaml` 只有 ruff + prettier，缺少：
- mypy（只在 CI 跑，本地不跑—容易“推到 CI 才发现类型错误”）
- 前端 lint（eslint 没进 pre-commit）

---

## 七、文档体系

[docs/](docs/) + [developer/](developer/) 双轨文档体系是亮点。42 个工单中有 41 个已完成、1 个待开始、1 个取消 — 工单管理健康。

**缺的文档：**
- `developer/release-checklist.md` — 已在中台角色草案中标注为后续可演进方向，未实际落地
- `developer/environment.md` — 环境变量清单散落在各文件中（`.env`、`config.py`、`fetcher.py` 的 TTL 变量、`__init__.py` 的 `CORS_ORIGINS`），缺少统一说明

---

## 八、改进路线图

按优先级排列：

### P1 — 应该立即修
1. **静默吞错加日志** — [watchlist_service.py](src/zhanfa/api/services/watchlist_service.py) 和 [data.py](src/zhanfa/api/routers/data.py) 所有 `except Exception: pass` 至少加 `logger.warning`
2. **`init_db()` 移出模块顶层** — [\__init__.py](src/zhanfa/api/__init__.py) 移到 lifespan 内
3. **`MinuteCacheStatus()` 可变默认值** — [models.py:367](src/zhanfa/api/models.py#L367) 改为 `Field(default_factory=MinuteCacheStatus)`

### P2 — 应该在下一个工单里修
4. **前端类型映射收敛** — client.ts 三个 `*ToResult` 合为一个
5. **前后端契约对齐** — StockInfo 要么补齐，要么改类型
6. **配置值与实际值对齐** — config.update_hour vs 调度时间
7. **DB 调度时间从 Config 读取**

### P3 — 技术债务，择机处理
8. **策略注册 fallback 从 DB 动态生成**
9. **get_watchlist_quotes 的 N+1 问题** — batch fetch
10. **日期格式统一到后端 validator**
11. **frontend 补齐 DataPage 测试**
12. **Docker nginx upstream 健康检查**

### P4 — 基础设施改进
13. **pre-commit 加 mypy + eslint**
14. **补齐 release-checklist.md 和 environment.md**
15. **backend scheduler 端到端集成测试**

---

## 九、结语

这个项目的代码质量在独立开发者/小团队的金融量化系统里属于**中上水准**。架构分层干净、测试体系扎实、mock 设计精巧。当前最拖后腿的不是架构缺陷，而是**静默吞错**带来的生产排障成本 — 一个 `except: pass` 在凌晨 debug 时就是半小时的盲猜。

整体来看，45 个文件的核心代码、295+153 的测试矩阵、全量通过无失败 — 项目处于健康的可交付状态。TICKET-042 是目前唯一待开工项（CI pytest 编码问题），如果前述 P1 项能顺手修掉，这个代码库就能从“写得好”升级到“跑得稳”。

---

*工程中台 | 2026-05-06 | 审查抽检了全部 35 个 Python 源文件、15 个前端 TS/TSX 源文件、全部测试文件、CI/Docker 配置*

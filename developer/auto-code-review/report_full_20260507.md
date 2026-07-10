# 工程中台 · 全量代码审查报告 (第二轮)

> 审查时间：2026-05-07 | 审查范围：全仓库 | 基于上轮报告 (2026-05-06) 的增量审查

---

## 〇、上轮问题修复状态

本轮审查对比上轮报告，未提交的 working copy 已修复 **11 项**，以下逐项核对：

| # | 上轮问题 | 状态 |
|---|---------|------|
| P1.1 | 静默吞错加日志 (watchlist_service) | ✅ 已修复 — 所有 `except: pass` 改为 `logger.warning()` |
| P1.2 | `init_db()` 移出模块顶层 | ✅ 已修复 — 移至 lifespan 管理 |
| P1.3 | `MinuteCacheStatus()` 可变默认值 | ✅ 已修复 — `Field(default_factory=MinuteCacheStatus)` |
| P2.4 | 前端类型映射收敛 (3→1) | ❌ 未修复 — client.ts 仍有三份 mapper |
| P2.5 | StockInfo 契约对齐 | ❌ 未修复 — `fetchStock()` 返回 `latest_financial` 不在类型中 |
| P2.6 | 配置值与实际值对齐 | ✅ 已修复 — 调度时间从 `Config` 读取 |
| P3.8 | 策略注册 fallback 从 DB 动态生成 | ❌ 未修复 — `BUILTIN_CODE_REFS` 硬编码 fallback 仍存在 |
| P3.9 | get_watchlist_quotes N+1 问题 | 🔶 部分修复 — 新增 batch 方法 (`last_closes`, `date_ranges`) 但 live fetch 仍逐个进行 |
| P3.10 | 日期格式统一 | ❌ 未修复 |
| P3.11 | DataPage 前端测试 | ❌ 未修复 |
| P3.12 | Docker nginx upstream 健康检查 | ✅ 已修复 — frontend 增加 `depends_on backend condition: service_healthy` |
| P4.13 | pre-commit 加 mypy + eslint | 🔶 部分修复 — 已添加但设为 `stages: [manual]`，自动提交时不触发 |
| P4.14 | release-checklist.md / environment.md | ✅ 已创建 |
| P4.15 | backend scheduler E2E 测试 | ❌ 未修复 |
| P2.7 | DB 调度时间从 Config 读取 | ✅ 已修复 |
| - | IndustryPeer 默认值 `float=0` | ✅ 已修复 — 改为 `float\|None = None` |

**小结：** 已修复 8 项，部分修复 2 项，未修复 5 项。本轮新发现 21 项。

---

## 一、新增 Critical 问题

### C0. Store 路径遍历漏洞 (安全)
**文件：** `src/zhanfa/data/store.py:20-21`
**严重级别：** Critical

```python
def _path(self, code: str, freq: str = "daily") -> Path:
    return self.base / freq / f"{code}.parquet"
```

Stock codes 从 API 端点直接传入 `store._path()`。若恶意请求发送 `../../etc/passwd` 作为 `code`，可构造任意路径访问文件系统。`load()`, `save()`, `delete()`, `exists()`, `mtime()` 均受影响。

**建议修复：** 在所有 API 入口验证 stock code 格式为 6 位数字；在 `Store._path()` 中增加路径遍历拦截。

### C1. `_tasks` 字典无线程安全保护
**文件：** `src/zhanfa/api/services/backtest_service.py:27`
**严重级别：** Critical

```python
_tasks: dict[str, dict] = {}  # 模块级共享可变状态
```

`_tasks` 被 FastAPI 的 async handler + `run_in_executor` 线程池 + `BackgroundTasks` 同时访问。`submit_backtest()` 写入、`run_backtest_async()` 读写、`get_task()` 读取均无 `threading.Lock` 保护。

**风险：** 并发提交回测时，dict 写入可能触发 rehash 导致其他线程读到损坏的中间状态，极端情况下抛出 `RuntimeError: dictionary changed size during iteration`。

**建议修复：**
```python
import threading
_lock = threading.Lock()

def submit_backtest(request: dict) -> str:
    ...
    with _lock:
        _tasks[task_id] = {...}
```

### C2. `_strategy_name_for()` 引发 N 次 DB 查询
**文件：** `src/zhanfa/api/services/backtest_service.py:327-335`
**严重级别：** High

```python
def _db_row_to_history_item(row: BacktestResult) -> dict:
    ...
    "strategy": _strategy_name_for(row.strategy_id),  # 每个 history item 一次 DB 查询
```

`get_history()` 对每条历史记录调用 `_strategy_name_for()`，每条记录打开/关闭一个 Session。若 history 有 100 条 = 100 次 DB 往返。

**建议修复：** 在 `_get_db_history()` 中预先查询所有 strategy_id → name 映射，批量载入。

### C3. Task ID 碰撞风险
**文件：** `src/zhanfa/api/services/backtest_service.py:124`
**严重级别：** Medium

```python
task_id = str(uuid.uuid4())[:8]  # 32 bits 熵
```

UUID4 截取前 8 个 hex 字符仅有 2^32 ≈ 40 亿个可能值。在中等负载下（10K tasks/年），生日悖论导致碰撞概率约 1%。建议使用完整 UUID 或 UUID4[:12]。

### C4. `navigate()` 在 render body 中被调用 (React 规则违反)
**文件：** `frontend/src/pages/backtest/BacktestPage.tsx:34-36`
**严重级别：** Critical

```typescript
if (pollResult && pollResult.status === 'done' && taskId) {
  navigate({ to: '/backtest/$backtestId', params: { backtestId: String(pollResult.id) } });
}
```

`navigate()` 在 render 函数体中直接调用而非在 `useEffect` 中。每次渲染都可能触发导航，违反 React 规则，可能导致无限重渲染循环。

**建议修复：** 移入 `useEffect` 并正确设置依赖数组。

### C5. KlineChart 跨线 handler 的过期闭包
**文件：** `frontend/src/components/chart/KlineChart.tsx:151-160`
**严重级别：** Critical

`chart.subscribeCrosshairMove` 回调捕获了图表创建时的 `data`。当用户切换频率后 `data` 变化，但图表实例被复用，crosshair handler 仍引用旧数据数组，导致 OHLCV 值来自错误的频率。

**建议修复：** 使用 `useRef` 保持 `data` 引用始终最新。

### C6. Alembic 迁移文件被 gitignore
**文件：** `.gitignore` 第 16 行
**严重级别：** Critical

`.gitignore` 包含 `alembic/versions/`，导致整个迁移版本目录被忽略。`a1b2c3d4e5f6_add_backtest_task_id.py` 未被 git 跟踪，未来所有迁移文件都不会纳入版本控制。

**建议修复：** 立即从 `.gitignore` 删除 `alembic/versions/`，`git add` 该迁移文件。

---

## 二、新增 High 问题

### H1. 残余 `except Exception: pass`
**文件：** `src/zhanfa/api/services/stock_service.py:53, 196`, `src/zhanfa/data/store.py:214`

虽然 `watchlist_service.py` 和 `data.py` 已修复，但还有三处静默吞错：

- **stock_service.py:53** — `get_stock_meta()` 中 DB 查询的 `except Exception: pass`，当数据库故障时该股票的所有扩展字段（exchange, industry）静默为空。
- **stock_service.py:196** — `get_industry_comparison()` 循环内的 `except Exception: pass`，单只股票出错无日志，排障困难。
- **store.py:214** — `stats()` 扫描循环中的 `except Exception: pass`，损坏的 parquet 文件被静默跳过。

**建议：** 统一改为 `logger.warning(..., exc_info=True)`。

### H2. `_create_db_record` rollback 可能失败
**文件：** `src/zhanfa/api/services/backtest_service.py:87-88`
**严重级别：** Medium

```python
except Exception:
    session.rollback()  # 若异常发生在 commit 前事务未启动，rollback 可能抛出新异常
```

SQLAlchemy 在没有活跃事务时调用 `rollback()` 是安全的（会静默忽略），但最安全的做法是先检查 `session.is_active`。当前代码风险较低但不可靠。

### H4. Dockerfile 构建失败 — `uv sync` 缺少源代码
**文件：** `Dockerfile:5-6`
**严重级别：** High

`COPY pyproject.toml uv.lock ./` 之后立即 `RUN uv sync --no-dev`，但 `src/` 尚未复制。若项目以可编辑模式安装，uv 会因找不到源代码而构建失败。

**建议修复：** 改为先 `uv sync --no-dev --no-install-project`，`COPY src/ src/` 后再 `uv sync --no-dev`。

### H5. vitest v2 与 vite v8 不兼容
**文件：** `frontend/package.json:49`
**严重级别：** High

`"vitest": "^2.0.0"` 与 `"vite": "^8.0.10"` 版本不兼容。Vitest 主版本需与 Vite 匹配。

**建议修复：** 升级到 `"vitest": "^3.0.0"`。

### H6. TypeScript 未启用 strict 模式
**文件：** `frontend/tsconfig.app.json`
**严重级别：** High

`tsconfig.app.json` 未设置 `"strict": true`。`strictNullChecks`、`noImplicitAny`、`strictFunctionTypes` 等均未开启，大量类型安全隐患不会被捕获。

**建议修复：** 添加 `"strict": true`。

### H7. `useBacktest` 只发送第一只股票代码
**文件：** `frontend/src/hooks/useBacktest.ts:23`
**严重级别：** High

```typescript
code: data.stock_codes[0]
```

用户可能选择多只股票，但只有 `stock_codes[0]` 被发送到后端。其余代码被静默丢弃。

**建议修复：** 支持多股回测，或限制 UI 为单选并更新类型。

### H8. 数据库凭据硬编码在 docker-compose.yml
**文件：** `docker-compose.yml:37-39`
**严重级别：** High

`POSTGRES_USER: zhanfa` 和 `POSTGRES_PASSWORD: zhanfa` 直接写死在版本控制中。

**建议修复：** 改为环境变量引用 `${POSTGRES_PASSWORD:-zhanfa}`。

### H3. `initialize` 端点阻塞
**文件：** `src/zhanfa/api/routers/data.py:85-90`
**严重级别：** Medium

`POST /api/data/initialize` 同步调用 `fetcher.stock_list()` → `import_stocks()` 遍历全市场 5000+ 股票并逐条 INSERT。整个过程可能耗时 30+ 秒，期间 FastAPI event loop 被阻塞，所有其他请求排队。

**建议：** 改为 `async def` + `run_in_executor`，或返回 `202 Accepted` 并以后台任务执行。

---

## 三、新增 Medium 问题

### M1. `mapBacktestStatus` 类型不安全
**文件：** `frontend/src/api/client.ts:254-258`
**严重级别：** Medium

```typescript
function mapBacktestStatus(status: string): BacktestResult['status'] {
  if (status === 'completed') return 'done';
  if (status === 'pending' || status === 'running' || status === 'failed') return status;
  return 'pending';  // 兜底：任何未知状态 → pending
}
```

后端返回的任何新状态值（如 `"cancelled"`）会被静默映射为 `"pending"`，用户看到"回测一直在排队"。应该在 unknown status 时至少打 `console.warn`。

### M2. `useChartData` 空数据下类型断言不安全
**文件：** `frontend/src/hooks/useChartData.ts:96`
**严重级别：** Medium

```typescript
indicators: null as unknown as ChartIndicatorResults
```

通过 `unknown` 双重强制转换将 `null` 断言为复杂对象类型。当 loading 为 true 但组件在数据到达前访问 `indicators.sma5` 会得到 `TypeError: Cannot read properties of null`。

**建议：** 类型声明改为 `ChartIndicatorResults | null`，组件内判空。

### M3. `metrics.py` `_estimate_years` 除零风险
**文件：** `src/zhanfa/backtest/metrics.py:84`
**严重级别：** Low (已兜底)

```python
return max(days / 365.25, 0.1)
```

当前有 `max(..., 0.1)` 兜底所以不会除零，但 `total_return` 计算 (`equity.iloc[-1] / equity.iloc[0]`) 在 `equity.iloc[0] == 0` 时会抛 `ZeroDivisionError`。概率极低但缺乏防护。

### M4. `vectorbt` `.stats()` 返回值类型
**文件：** `src/zhanfa/backtest/report.py:49-57`
**严重级别：** Low

```python
stats = pf.stats()
f"| 总交易次数 | {stats.get('Total Trades', 0)} |"
```

`pf.stats()` 返回 `pd.Series`，不是 `dict`。在 `pd.Series` 上 `.get()` 表现与 `dict.get()` 不同（Series.get 接受 key 和 default 但语义不同）。虽然当前能工作，但应在类型上更明确。

### M5. `scheduler.py` `_next_run_times` 依赖内部 API
**文件：** `src/zhanfa/automation/scheduler.py:193-194`
**严重级别：** Low

```python
label = (
    job.job_func.keyword.get("label", "")
    if hasattr(job.job_func, "keyword") and job.job_func is not None
    else ""
)
```

`schedule` 库的 `job.job_func` 内部结构（`functools.partial` 上的 `keyword` 属性）是非公开 API，跨版本可能变化。建议在 `register_func` 时自行维护 `job_label → next_run` 映射表。

### M6. `export_csv` 中 N+1 查询
**文件：** `src/zhanfa/api/services/watchlist_service.py:474-486`
**严重级别：** Low

```python
for item in wl.items:
    stock = db.get(Stock, item.code)  # 每个 item 一次 DB 查询
```

与 `_strategy_name_for` 同类问题。在 50 只股票的自选股分组中就是 50 次查询。

### M7. `watchlist_service` 返回类型不一致
**文件：** `src/zhanfa/api/services/watchlist_service.py:65-73`
**严重级别：** Low

`delete_watchlist(db, wl_id)` 返回 `tuple[bool, str]`，但同模块的 `create_watchlist`、`update_watchlist`、`add_item` 等全部返回 `dict | None`。调用方需要区分两种返回形状。

### M8. `fetcher.py` `industry_stocks()` 异常静默
**文件：** `src/zhanfa/data/fetcher.py:226-227`
**严重级别：** Low

```python
except Exception:
    return pd.DataFrame(columns=["code", "name"])
```

若 `akshare` 调用失败（网络、API 变更等），返回空 DataFrame 且无日志。调用方（`get_industry_comparison`）将其解释为"无同行公司"，语义混淆。

### M9. `create_app()` 模块级调用
**文件：** `src/zhanfa/api/__init__.py:113`
**严重级别：** Low

```python
app = create_app()  # 模块导入时即执行，含默认 init_database=True, start_scheduler=True
```

虽然 `init_db()` 已移入 lifespan（不阻塞导入），但 scheduler 线程仍在 lifespan 中启动。如果通过 `uvicorn` 以 `--reload` 模式运行，每次文件变更都会创建新线程而旧线程未清理。建议在测试/CLI 场景显式传入 `start_scheduler=False`。

### M10. Alembic `env.py` 导入触发完整模块初始化
**文件：** `alembic/env.py:17-18`
**严重级别：** Low

```python
from zhanfa.db.base import Base
import zhanfa.db.models  # noqa: F401
```

`zhanfa.db.base` 导入会触发 `config.py` → `Config()` dataclass 实例化，包括环境变量读取。在 CI 环境中若 `DATABASE_URL` 未正确设置，migration 命令会失败，错误信息不直观。

---

## 四、仍未修复的上轮问题（再次列出）

### U1. 前端类型映射三份 → 一份
**文件：** `frontend/src/api/client.ts:354-452`
**状态：** 未修复

三个函数 `historyItemToResult`、`taskToResult`、`strategyResultToBacktestResult` 都通过 `buildBacktestResult()` 构建相同结构。虽然已经抽取了公共 `buildBacktestResult`，但三个入口仍各自做字段名映射（`item.task_id` → `input.id` 等），应进一步收敛为单个 `normalizeBacktestResult(raw: unknown): BacktestResult`。

### U2. StockInfo 类型与返回值不一致
**文件：** `frontend/src/types/index.ts:81-88` ↔ `src/zhanfa/api/services/stock_service.py:31-63`
**状态：** 未修复

`fetchStock()` 声明返回 `StockInfo | undefined`，但 `get_stock_meta()` 实际返回包含 `latest_financial` 的对象。同时 `exchange`、`industry`、`market_cap` 在 types 中标为可选，但 service 层返回 `None` 硬值。

### U3. 日期格式双轨
**文件：** `src/zhanfa/api/services/backtest_service.py:30-35` + `frontend/src/api/client.ts:499`
**状态：** 未修复

仍存在 `"20200101"` ↔ `"2020-01-01"` 双向转换分散在前后端。

### U4. 策略注册硬编码 fallback
**文件：** `src/zhanfa/api/services/strategy_service.py:145-153`
**状态：** 未修复

`_resolve_code_ref()` 在 DB 查询失败后 fallback 到 `BUILTIN_CODE_REFS`。新增策略需同时更新 DB（通过 `register_strategies()`）和 `registry.py`。应改为从 DB 动态读取或仅依赖 DB。

### U5. 缺少 DataPage 前端测试
**状态：** 未修复

`DataPage.tsx` 仍无测试覆盖。refresh/stats/stock-status 三条关键路径缺少 UI 层验证。

### U6. 缺少 Scheduler E2E 测试
**状态：** 未修复

`scheduler` 模块有单元测试但无 `schedule → fetch → cache` 全链路集成测试。

### U7. Pre-commit mypy + eslint 为手动阶段
**文件：** `.pre-commit-config.yaml:17-28`
**状态：** 未修复（上周已添加但设为 `stages: [manual]`）

mypy 和 eslint 在自动提交时不运行，需要手动 `pre-commit run --hook-stage manual`。失去了 pre-commit 自动拦截的价值。

### U8. 前端缺失 ESLint/Prettier 配置文件
**状态：** 新发现

`frontend/package.json` 依赖了 `eslint` 和 `prettier`，但 `frontend/` 目录下无 `.eslint.config.js`、`.prettierrc` 等配置文件。`npm run lint` 可能使用 eslint 默认配置，规则不完整。

---

## 五、测试缺口汇总

| 缺口 | 严重级别 | 描述 |
|------|---------|------|
| `_tasks` 并发竞态 | Critical | 无并发测试覆盖 `submit_backtest` 的线程安全 |
| Parquet 损坏降级 | High | 无 parquet 文件损坏后的 `Store` 降级行为测试 |
| Scheduler E2E | Medium | 无 `schedule → fetch → cache` 全链路测试 |
| DataPage UI | Medium | 无 DataPage 组件测试 |
| 图表组件数据转换 | Low | 无 `aggregateData` / `ChartIndicatorResults` 纯函数测试 |
| `initialize` 端点 | Low | 无超时/失败场景测试 |

---

## 六、改进路线图 (2026-05-07)

### P1 — 立即修复（安全/可靠性）
1. **C1**: `_tasks` dict 加 `threading.Lock`
2. **H1**: 剩余三处 `except: pass` 加 logger.warning

### P2 — 本轮应修
3. **C2**: `_strategy_name_for` 改为批量查询
4. **C3**: task_id 使用完整 UUID
5. **H3**: `initialize` 端点改为异步/后台任务
6. **U7**: pre-commit mypy+eslint 设为自动阶段

### P3 — 技术债务
7. **U1**: 前端类型映射收敛为单个 normalize 函数
8. **U2**: StockInfo 类型对齐
9. **U3**: 日期格式统一到后端 validator
10. **U4**: 移除 `BUILTIN_CODE_REFS` 硬编码 fallback
11. **H2**: `_create_db_record` rollback 安全检查

### P4 — 择机改进
12. **M1**: `mapBacktestStatus` unknown status 告警
13. **M2**: `useChartData` 类型 safety
14. **M3-M10**: 各项 Low 级问题
15. **U5, U6**: DataPage 测试、Scheduler E2E 测试
16. **U8**: 前端 ESLint/Prettier 配置文件

---

## 七、总结

相比上轮审查，项目在以可见速度改进 — P1 项全部修复、文档补齐、Docker 健康检查完善。本轮新发现的主要是**并发安全**和**剩余静默吞错**两类问题，深度比上轮更细。

核心建议：**先修 `_tasks` 锁（C1）+ 剩余 `except: pass`（H1）+ 批量查询（C2）**，这三个加起来改动量 < 50 行但能消除当前最大的生产风险。其余可按优先级排入后续工单。

---

*工程中台 | 2026-05-07 | 全量审查 35 个 Python 源文件 + 22 个 TS/TSX 源文件 + 全部配置/测试/CI 文件*

# Debug Notes

常见问题排查记录。

## 策略入口显示异常

**症状**: 前端策略列表/详情页显示英文标识符而非中文名称，或报错。

**排查**:

1. 检查 `frontend/.env` 中 `VITE_ENABLE_MOCK`：`true` 用 mock 数据，`false` 调后端 API
2. 检查 DB 中的策略注册状态：
   ```bash
   python -c "
   from zhanfa.db.base import SessionLocal
   from zhanfa.db.models import Strategy
   s = SessionLocal()
   for r in s.query(Strategy).order_by(Strategy.id).all():
       print(f'id={r.id} name={r.name} code_ref={r.code_ref is not None}')
   s.close()
   "
   ```
3. `code_ref` 必须是完整模块路径 `package.module.ClassName`（如 `zhanfa.strategies.trend.sma_cross.SMACross`）
4. 删除 `code_ref = NULL` 的孤儿策略

## 策略名更新后 DB 不生效

`register_strategies()` 在 FastAPI lifespan 中通过 `code_ref` 做 upsert，重启后端即可。如果仍不生效：确认 `code_ref` 一致、`name` 在类定义中（非实例属性）、无唯一约束冲突。

## 回测提交失败

**症状**: 返回 500 或 `ValueError: Unknown strategy`。

1. 确认 `strategy` 字段是有效 `code_ref`：`curl -s http://127.0.0.1:8000/api/strategies | python -m json.tool | grep code_ref`
2. 验证解析：`python -c "from zhanfa.api.services.strategy_service import _resolve_code_ref; print(_resolve_code_ref('zhanfa.strategies.momentum.rsi_strategy.RSIStrategy'))"`
3. 如 DB 不可用，检查 `_resolve_code_ref` 的 fallback 字典

## akshare 中文列名在 Windows GBK 终端乱码

**症状**: akshare 返回的 DataFrame 列名为 UTF-8 编码的中文字符，在 Windows GBK (cp936) 终端下 print 显示为乱码（如 `����`）。

**根本原因**: Python 3.x 在 Windows 终端默认使用系统代码页（GBK/cp936），而 akshare 底层（东方财富/新浪 API）返回 UTF-8 数据。当 `PYTHONIOENCODING` 未设置时，`print()` 尝试将 UTF-8 字符串编码为 GBK 输出，中文字符无法映射导致乱码。

**解决方案**:
```python
import os
os.environ["PYTHONIOENCODING"] = "utf-8"
```
放在所有 import 之前。此设置强制 Python 使用 UTF-8 进行标准输出编码。

**注意**:
- 仅在 Windows 中文环境需要；Linux/macOS 默认 UTF-8 不受影响
- `stock_zh_a_hist_min_em` 返回中文列名（时间/开盘/收盘/最高/最低/成交量/成交额/涨跌幅/涨跌额/振幅/换手率），映射表见 [fetcher.py:136-140](src/zhanfa/data/fetcher.py)
- `stock_zh_a_minute` (Sina) 返回英文列名（day/open/high/low/close/volume/amount），无此问题
- Notebook (.ipynb) 环境通常已是 UTF-8，不受影响

## 2026-05-05 全面代码审查 Debug 工单

本次审查将 7 个发现拆分为独立工单：

- `TICKET-031`: 前端生产构建失败。已取消并拆分为 `TICKET-038`、`TICKET-039`、`TICKET-040`。
- `TICKET-032`: API 测试隔离数据库。测试导入生产 app 后写入默认 `data/zhanfa.db`，导致唯一约束冲突和测试污染。
- `TICKET-033`: 修复回测止损/止盈参数语义。`vectorbt` 的 `sl_stop/tp_stop` 应直接传入 0.1/0.3 等比例距离，不能转换为 0.9/1.3。
- `TICKET-034`: 回测结果持久化与策略结果联动。当前 `_tasks` 是进程内存，服务重启丢失历史，策略详情无法看到新回测。
- `TICKET-035`: 数据刷新 `freq` 参数被忽略。分钟级强制刷新会删除分钟缓存，但实际调用日线刷新。
- `TICKET-036`: 策略详情回测记录未按策略过滤。真实 API 模式忽略 `strategyId`，所有历史被映射成 `strategy_id: 0`。
- `TICKET-037`: 行业比较前端接入真实 API。后端接口已存在，前端真实模式仍返回 `undefined`。
- `TICKET-038`: 前端 TypeScript 配置与核心类型修复。
- `TICKET-039`: lightweight-charts v5 API 迁移。
- `TICKET-040`: 前端页面/组件严格类型清理。

验证命令记录：

```bash
uv run pytest -q       # 修复前: 216 passed, 2 failed；修复后: 220 passed
uv run ruff check src tests
uv run mypy src
cd frontend && npm run test   # 129 passed
cd frontend && npm run build  # 修复后通过；仍有 Vite chunk size warning
```

2026-05-05 并行修复记录：

- `TICKET-032`: 使用独立临时 SQLite 文件库运行测试，避免污染 `data/zhanfa.db`；内存 SQLite 在线程池执行回测时会因连接隔离导致 `no such table`。
- `TICKET-033`: `sl_stop` / `tp_stop` 直接按 vectorbt 的比例距离语义传入，例如 `0.1` 表示 10%。
- `TICKET-038` / `TICKET-039` / `TICKET-040`: 取消原 `TICKET-031` 后拆分完成，前端生产构建恢复通过。

## 分钟级数据 (stock_zh_a_minute) 注意事项

**固定 1,970 行限制**: Sina `stock_zh_a_minute` 所有频率均固定返回 1,970 行，无法通过 `start_date` 参数获取更早数据。低频（bar 长）= 覆盖更多日历时间：1h 约 2 年，15min 约 6 个月，1min 约 8 天。

**volume/amount 为字符串**: Sina 返回的成交量/成交额 dtype 为 `str`（东方财富返回 `int64`/`float64`）。使用前必须 `pd.to_numeric()` 转换，否则 `Pipeline.clean()` 中的 `df['volume'] == 0` 判断会失败。

**东方财富 1d 不可用**: `stock_zh_a_hist_min_em(period="1d")` 返回单日盘中数据（240 行），不是日线 OHLC。日线数据请使用 `stock_zh_a_hist(period="daily")`。

**数据滚动**: Sina 的 1,970 行固定窗口会随交易日滚动。首次拉取只能拿到最近窗口，需持续 T+1 更新才能累积更长历史。

## parquet 缓存无过期机制导致读到截断/过期数据

**症状**: `Fetcher.stock_list()` 只返回 2 行（000001 和 000002），而实际全 A 股有 5500+ 行。`index_components()`、`industry_stocks()` 等 meta 类数据也可能长期不更新。

**原因**: `Store` 的 parquet 缓存没有 TTL 机制 — 一旦文件存在，`load()` 永远返回缓存内容，不会重新拉取。如果某次运行中写入了截断的 DataFrame（比如中断的下载、调试代码只 `head()` 了前几行），后续所有调用都会命中这份坏的缓存。

**已修复 (TICKET-041)**:
- `Store.load()` 新增 `max_age: timedelta | None` 参数，基于文件 mtime 判断过期
- `Store.mtime()` 返回缓存文件最后修改时间（UTC）
- `Fetcher` 各方法配置默认 TTL（通过环境变量可覆盖）：
  - `daily()` → 6h (`CACHE_TTL_DAILY_HOURS`)
  - `index_daily()` → 6h (`CACHE_TTL_INDEX_DAILY_HOURS`)
  - `stock_list()` → 24h (`CACHE_TTL_STOCK_LIST_HOURS`)
  - `index_components()` → 24h (`CACHE_TTL_INDEX_COMPONENTS_HOURS`)
  - `industry_stocks()` → 24h (`CACHE_TTL_INDUSTRY_STOCKS_HOURS`)
  - `financial()` → 30d (`CACHE_TTL_FINANCIAL_HOURS`)
  - `minute()` → 6h (`CACHE_TTL_MINUTE_HOURS`)
- 缓存完整性校验：`stock_list()` 要求 ≥5000 行，`daily()` 要求 ≥1 行；坏缓存自动删除并重新拉取
- 调度器自动刷新：15:30 更新日线、15:45 更新分钟线、周五 16:00 指数调仓

## 数据初始化与自选股外键

**症状**: 空数据库环境中，股票搜索能从 akshare 返回结果，但添加到自选股时报外键错误；数据管理页统计长期为 0。

**原因**: `watchlist_items.code` 指向 `stocks.code`，而早期刷新流程只写 parquet 缓存，不会把 `stock_list` 导入 `stocks` 表。

**当前约定**:

- `POST /api/data/initialize` 拉取并缓存全 A 股列表，然后导入 `stocks`。
- `POST /api/data/refresh` 在 `discover_new=true` 时同步导入股票元信息，再拉取日线。
- `add_item()` / `batch_add_items()` 会在写入自选股前确保缺失的 `Stock` 记录存在，避免 FK 错误。

## 前端构建 & API 测试

```bash
cd frontend && npx tsc --noEmit   # 类型检查
cd frontend && npx vite build     # 生产构建

# 常用 API
curl http://127.0.0.1:8000/api/strategies      # 策略列表
curl http://127.0.0.1:8000/api/strategies/1     # 策略详情
curl http://127.0.0.1:8000/api/health           # 健康检查
```

## 2026-05-06 仓库问题复查与工单拆分

本次复查确认用户列出的 6 类问题仍可在当前代码中定位，并额外发现 2 个同源风险，已拆为独立需求工单：

- `TICKET-043`: API 降级路径静默吞错缺少可观测性。覆盖 `watchlist_service` 与 `data` router 中的 `except Exception: pass`。
- `TICKET-044`: 移除 FastAPI 模块导入阶段的 `init_db()` 副作用。
- `TICKET-045`: Pydantic 模型可变默认值统一改为 `Field(default_factory=...)`，不只 `MinuteCacheStatus()`，还包括多个 `{}` / `[]` 字段默认值。
- `TICKET-046`: 前端 `BacktestResult` 三个映射函数去重，降低字段扩展遗漏风险。
- `TICKET-047`: `StockInfo` 前后端契约对齐。后端只返回 `code/name`，前端要求 `exchange/industry/market_cap/listed_date`。
- `TICKET-048`: `get_watchlist_quotes()` 批量行情查询性能优化，避免自选股多时逐只串行读取/抓取。
- `TICKET-049`: 行业比较接口逐股抓取财务数据导致响应慢。
- `TICKET-050`: 回测结果持久化失败缺少日志与失败语义。

复查命令记录：

```bash
Get-ChildItem -Recurse -Include *.py -Path src | Select-String -Pattern 'except','pass'
Get-ChildItem -Recurse -Include *.py,*.ts,*.tsx -Path src,frontend | Select-String -Pattern 'init_db\(','MinuteCacheStatus','ToResult','StockInfo','get_watchlist_quotes'
Get-ChildItem -Recurse -Include *.py -Path src | Select-String -Pattern '= \{\}|= \[\]|= [A-Za-z_][A-Za-z0-9_]*\(\)'
```

## 2026-05-06 中台全量代码审查报告对接

已对接 `developer/auto-code-review/report_full_20260506.md` 中提出的问题。覆盖关系如下：

| 报告问题 | 对应工单 | 备注 |
|----------|----------|------|
| 静默吞错加日志 | `TICKET-043` | P1，覆盖 `watchlist_service` 与 `data` router |
| `init_db()` import 副作用 | `TICKET-044` | P1，迁入 FastAPI lifespan 或 app factory |
| `MinuteCacheStatus()` 可变默认值 | `TICKET-045` | P1，同时覆盖其他 `{}` / `[]` 默认值 |
| 前端三个回测结果 mapper 重复 | `TICKET-046` | P2，含 trade action 类型保护 |
| `StockInfo` 前后端契约不一致 | `TICKET-047` | P2，含 `fetchStock()` 硬填字段问题 |
| `get_watchlist_quotes()` N+1 | `TICKET-048` | P3 |
| 日期格式双轨制 | `TICKET-051` | P2，统一由后端 validator 处理 |
| `Config.update_hour` 与实际调度时间不一致 | `TICKET-052` | P2 |
| 策略注册 fallback 双轨制 | `TICKET-053` | P3 |
| scheduler/parquet/backtest/DataPage/图表测试缺口 | `TICKET-054` | P2，合并为关键链路与降级测试 |
| Docker frontend 未等待 backend healthy | `TICKET-055` | P3 |
| pre-commit 缺 mypy/eslint | `TICKET-056` | P4 |
| release checklist 与 environment 文档缺口 | `TICKET-057` | P4 |
| 行业比较逐股抓财务数据 | `TICKET-049` | P3，本次复查额外发现，与报告 fan-out 风险同类 |
| 回测持久化失败吞日志 | `TICKET-050` | P2，本次复查额外发现 |

两处报告内容按当前代码核对后未重复开工单：

- 报告称 `_register_scheduler_tasks()` 顶层启动后台线程；当前代码中线程启动发生在 `lifespan()` 调用链内，真正仍需处理的是调度时间配置化，见 `TICKET-052`。
- 报告建议 CI npm cache；当前 `.github/workflows/ci.yml` 已使用 `actions/setup-node@v4` 的 `cache: npm` 和 `cache-dependency-path: frontend/package-lock.json`，暂不拆工单。

## 2026-07-12 akshare 误继承系统代理导致东方财富抓取失败

**症状**: 日线更新中单只股票失败，日志包含 `push2his.eastmoney.com`、`ProxyError('Unable to connect to proxy')`、`Remote end closed connection without response`。

**定位**: 当前 Python 进程能看到 `HTTP_PROXY` / `HTTPS_PROXY=http://127.0.0.1:7890`，akshare 底层 HTTP 请求继承这些环境变量后，东方财富请求被转发到本机代理。代理端断开时，`update_daily_data()` 只会把该股票记为失败并继续批次。

**修复 (TICKET-064)**:
- `Fetcher` 的 akshare 网络调用统一走内部入口。
- 默认临时屏蔽 `HTTP_PROXY`、`HTTPS_PROXY`、`ALL_PROXY`、`NO_PROXY` 及小写形式。
- 需要代理时显式设置 `ZHANFA_AKSHARE_USE_PROXY=true`。

**复查命令**:

```bash
uv run pytest tests/test_data/test_fetcher.py -q
uv run ruff check src/zhanfa/data/fetcher.py tests/test_data/test_fetcher.py
uv run mypy src/
```

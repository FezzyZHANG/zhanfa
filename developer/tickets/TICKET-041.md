# TICKET-041: 数据缓存可知情与定期更新

**优先级:** P1 - 高
**状态:** ✅ 已完成
**依赖:** -
**预计工时:** 2d

## 需求描述

当前 parquet 缓存无 TTL、无自动刷新、无 staleness 感知，用户无法判断缓存数据是否过期。需补齐三个能力：缓存可知情（每个缓存文件何时更新、数据新鲜度）、定期自动更新（调度器注册日线/元数据刷新任务）、缓存过期策略（不同类型数据有不同保鲜期）。

## 现状问题

### 1. 缓存无过期机制
- `Store.load()` 只要文件存在就返回，永不重新拉取
- `Fetcher` 所有方法都是 cache-first，缓存命中后跳过 akshare
- 一旦写入截断/过期数据，后续调用永久读到坏缓存
- debug-notes.md 已记录此问题

### 2. 缓存新鲜度不透明
- `data_freshness` 字段只有 `"cached"` / `"live"` / `"unknown"`，不体现缓存年龄
- `CacheStats`、`StockDataStatus` 缺少 `last_updated` 时间戳
- 前端 DataPage 显示日期范围但不知道数据是什么时候缓存的
- 用户无法判断缓存是 1 小时前还是 1 个月前更新的

### 3. 调度器空转
- `automation/scheduler.py` 框架已就绪（`Scheduler` 类、`daily()`/`hourly()` 装饰器、持久化）
- 但全局 `scheduler` 实例未注册任何任务
- `POST /api/scheduler/trigger` 端点存在但需手动调用
- 没有自动刷新日线、元数据、财务数据的定时任务

### 4. 不同数据类型无差异化 TTL
- 日线行情：收盘后可刷新，合理 TTL = 1 个交易日
- 元数据（stock_list、成分股）：变化频率低，合理 TTL = 1 天
- 财务数据：季度更新，合理 TTL = 1 季度
- 分钟线：盘后更新，合理 TTL = 1 天
- 当前：全部永久缓存，无差异化策略

## 任务清单

### Phase 1 — 缓存时间戳与可知情

- [ ] `Store` 增加 `mtime(code, freq)` 方法：返回缓存文件的最后修改时间
- [ ] `CacheStats` 模型增加 `last_refreshed_at: datetime | None`
- [ ] `StockDataStatus` 增加 per-freq 的 `cached_at: datetime | None`
- [ ] `GET /api/data/stats` 返回全局最新刷新时间
- [ ] `GET /api/data/stock-status` 返回每只股票每种频率的缓存时间
- [ ] 前端 DataPage 展示缓存更新时间

### Phase 2 — 缓存 TTL 与过期策略

- [ ] `Store` 增加 `max_age` 参数：`load(code, freq, max_age: timedelta | None = None)`
- [ ] `Fetcher` 各方法配置合理默认 TTL：
  - `daily()`: 6h（覆盖一个交易日）
  - `index_daily()`: 6h
  - `stock_list()`: 24h
  - `index_components()`: 24h
  - `industry_stocks()`: 24h
  - `financial()`: 30d
  - `minute()`: 6h
- [ ] `data_freshness` 字段改为体现年龄：`"cached_1h"` / `"cached_1d"` / `"stale"` 或类似粒度
- [ ] 前端 QuoteItem 展示 freshness 时附加可读的时间描述

### Phase 3 — 调度器注册自动刷新

- [ ] 在 `automation/scheduler.py` 注册 `update_daily_data` 为每日收盘后任务（如 15:30）
- [ ] 注册 `weekly_index_rebalance` 为每周五收盘后任务
- [ ] 注册 `update_minute_data` 为每日收盘后任务（覆盖已缓存股票）
- [ ] 调度器在 FastAPI lifespan 中启动后台线程
- [ ] 前端 Scheduler 页面可查看任务状态与下次执行时间
- [ ] 错误通知：刷新失败时记录日志并暴露在 `/api/scheduler/status`

### Phase 4 — 缓存完整性校验

- [ ] `Fetcher.stock_list()` 加载缓存后做行数校验（≥5000 行，防止截断缓存）
- [ ] `Fetcher.daily()` 加载缓存后做最小行数校验（≥1 行）
- [ ] 校验失败时自动删除坏缓存并重新拉取

## 验收标准

- [ ] `GET /api/data/stats` 返回 `last_refreshed_at` 字段
- [ ] `GET /api/data/stock-status?code=000001` 返回每种频率的 `cached_at`
- [ ] 缓存超出 TTL 后自动重新拉取（手动测试：修改 parquet 文件 mtime 到 2 天前，调用 fetcher 验证重新拉取）
- [ ] `GET /api/scheduler/status` 显示已注册的定时任务
- [ ] 调度器在后台自动执行（日志验证）
- [ ] 前端 DataPage 显示缓存更新时间
- [ ] 前端自选股面板 QuoteItem 显示可读的数据新鲜度
- [ ] 全量测试通过：`uv run pytest -q` 且 `cd frontend && npm run test`
- [ ] 缓存截断场景（stock_list 只有 2 行）触发自动修复

## 备注

- 与 debug-notes.md 中记录的 "parquet 缓存无过期机制" 直接对应
- TTL 基于文件 mtime 判断，不引入额外状态存储
- 调度器使用现有 `schedule` 库，不引入 Celery/Redis 等重依赖
- 默认 TTL 值可通过环境变量覆盖（如 `CACHE_TTL_DAILY_HOURS=1`）

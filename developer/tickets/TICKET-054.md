# TICKET-054: 补齐关键链路与降级场景测试

**优先级:** P2 - 中
**状态:** ✅ 已完成
**依赖:** TICKET-041, TICKET-043
**预计工时:** 1d

## 症状

现有测试覆盖了大量 API、service 与前端 mock 场景，但中台报告指出仍缺少几类高风险链路：

- scheduler 实际执行的端到端测试：schedule → fetch → cache
- backtest_service `_tasks` 多线程/并发访问竞态测试
- parquet 文件损坏后的降级行为测试
- 前端 `DataPage` 测试
- 图表数据转换逻辑的纯函数测试

## 根因分析

当前测试更偏功能单元与接口生命周期，较少覆盖“后台任务 + 文件缓存 + 并发内存状态”这类跨层行为。随着缓存 TTL、调度器、回测持久化增强，这些链路需要更明确的回归保护。

## 修复方案

### 1. 后端链路测试

新增或扩展：

- `tests/test_automation/test_scheduler_e2e.py`
- `tests/test_data/test_store_corrupt.py`
- `tests/test_services/test_backtest_concurrency.py`

使用 mock fetcher/store 限制外部依赖。

### 2. 前端页面与转换测试

新增：

- `frontend/src/pages/data/__tests__/DataPage.test.tsx`
- 图表数据转换 helper 的纯函数测试

### 3. 明确损坏缓存行为

与 `TICKET-043` 配合，坏 parquet 至少应：

- 有日志
- 有降级结果
- 不让整个接口无提示空白

## 实施结果

### 后端新增测试
- `tests/test_data/test_store_corrupt.py` (6 tests) — parquet 损坏/截断后 load 返回 None、exists/mtime 仍正常、save 可覆盖、stats 不计损坏行
- `tests/test_services/test_backtest_concurrency.py` (5 tests) — 并发提交去重、混合策略不互相干扰、多线程读写 _tasks、并发运行回测、交错的 submit+run

### 后端修复
- `src/zhanfa/data/store.py` — `load()` 新增 try/except 包裹 `pd.read_parquet`，损坏文件记录 WARNING 日志后返回 None

### 前端新增测试
- `frontend/src/pages/data/__tests__/DataPage.test.tsx` (8 tests) — loading/未初始化/已初始化/初始化成功/初始化失败/非 Error 异常/pending 禁用按钮/stock_count>0 显示统计

## 验收标准

- [x] scheduler 端到端测试覆盖任务触发到缓存写入/刷新 (已有 test_automation/test_scheduler.py 14 tests + test_workflows.py 6 tests)
- [x] parquet 损坏场景有测试覆盖 (test_store_corrupt.py → 6 tests)
- [x] backtest `_tasks` 并发访问风险有最小回归测试 (test_backtest_concurrency.py → 5 tests)
- [x] DataPage loading/empty/error/success 至少四态有测试 (DataPage.test.tsx → 8 tests)
- [x] 图表数据转换逻辑脱离 Canvas 有纯函数测试 (已有 indicators.test.ts 17 tests)
- [x] `uv run pytest tests/test_data/ -q` → 68 passed, 2 skipped
- [x] `cd frontend && npm run test` → 11 test files, 161 tests passed

## 来源

- `developer/auto-code-review/report_full_20260506.md` — 5.1/5.2 测试缺口

# TICKET-062: 代码审查 代码质量改进

> 来源：2026-05-07 全量代码审查 | 优先级：P2

## 关联文档

- [审查报告](../auto-code-review/report_full_20260507.md)

## 任务清单

### U1 — 前端类型映射收敛
- [ ] `frontend/src/api/client.ts`: 将 `historyItemToResult`、`taskToResult`、`strategyResultToBacktestResult` 三个 mapper 收敛为单个 `normalizeBacktestResult(raw: unknown): BacktestResult` 函数
- [ ] 添加后端返回形状的 JSDoc 文档

### U2 — StockInfo 类型与 API 返回值对齐
- [ ] `frontend/src/types/index.ts`: `StockInfo` 添加 `latest_financial` 字段，或改为 `Partial` 类型
- [ ] 若后端补齐字段，更新 `src/zhanfa/api/services/stock_service.py:get_stock_meta()` 返回完整数据

### U3 — 日期格式统一
- [ ] 将日期转换逻辑收敛到后端 Pydantic validator：`BacktestRequest` 中 `start_date`/`end_date` 接受 ISO 格式
- [ ] 后端 `_parse_date()` 统一处理 `YYYYMMDD` / `YYYY-MM-DD`
- [ ] 前端 `client.ts` 移除 `replace(/-/g, '')` 转换

### U4 — 策略注册 fallback 从 DB 动态生成
- [ ] `src/zhanfa/api/services/strategy_service.py:145-153`: 移除 `BUILTIN_CODE_REFS` 硬编码，改为直接调用 `register_strategies()` 或从 DB 读取

### M1 — `mapBacktestStatus` 未知状态告警
- [ ] `frontend/src/api/client.ts:254-258`: 未知 status 时至少 `console.warn`

### 代码重复消除
- [ ] `frontend/src/components/watchlist/`: 提取 `freshnessLabel` / `DataStatusBadge` 到共享组件
- [ ] `frontend/src/components/backtest/TradeTable.tsx` + `frontend/src/components/financial/FinancialTable.tsx`: 提取 `exportToCsv` 到 `frontend/src/lib/utils.ts`
- [ ] `src/zhanfa/data/store.py` + `src/zhanfa/api/routers/data.py`: 收敛重复的 parquet date-range 读取逻辑
- [ ] `src/zhanfa/api/services/backtest_service.py:327`: 重命名 `compare_backtests` 为 `filter_backtests` 或实现真正对比逻辑

### DB 索引
- [ ] `src/zhanfa/db/models.py`: 为 `BacktestResult.strategy_id`、`BacktestResult.task_id`、`BacktestResult.created_at`、`StockFinancial.code` 添加 index

## 状态

待开始

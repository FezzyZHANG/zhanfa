# TICKET-063: 代码审查 测试覆盖补齐

> 来源：2026-05-07 全量代码审查 | 优先级：P3

## 关联文档

- [审查报告](../auto-code-review/report_full_20260507.md)

## 任务清单

### 后端服务测试
- [ ] `tests/test_services/test_stock_service.py` (新建): 覆盖 `list_stocks`, `get_stock_meta`, `get_daily`, `get_financial`, `get_indicators`, `get_industry_comparison`
  - 缓存命中 / 未命中
  - 空结果
  - DB 不可用时降级
  - 财务数据为空时返回 shape

### 后端策略工具测试
- [ ] `tests/test_strategies/test_indicators.py` (新建): 覆盖 `sma`, `ema`, `macd`, `rsi`, `bollinger`, `donchian`, `atr`, `highest`, `lowest`
  - 已知输入/输出对 (手动计算验证)
  - 边界情况 (恒定价格、NaN 输入、短序列、除零)

### 后端报告测试
- [ ] `tests/test_backtest/test_report.py` (新建): 覆盖 `generate_report`, `save_report`
  - Mock Portfolio 验证报告文本格式
  - 含/不含 benchmark 的两种路径

### 后端并发测试
- [ ] `tests/test_services/test_backtest_concurrency.py`: 新增 `test_concurrent_submit_idempotent` 并发提交测试
- [ ] 验证 `_tasks` 加锁后并发场景无异常

### 前端 hooks 测试
- [ ] `frontend/src/hooks/useChartData.test.ts` (新建): `aggregateData` 的 W/M/Q/Y 聚合逻辑
- [ ] `frontend/src/hooks/useBacktest.test.ts` (新建): `submit` 函数参数传递验证
- [ ] `frontend/src/hooks/useWatchlistUrlFilters.test.ts` (新建): `applyFilters` 各种过滤组合

### 前端组件测试
- [ ] `frontend/src/pages/data/DataPage.test.tsx`: 补充实际数据流覆盖
- [ ] `frontend/src/components/watchlist/`: WatchlistTable / WatchlistCards 排序/筛选/批处理测试

### 修复已有测试问题
- [ ] `tests/test_automation/test_scheduler.py:127-128`: 修复自指断言 (`assert_called_once_with` 参数与自身比较)
- [ ] `tests/test_data/test_pipeline.py:123`: `or` → `and` (channel_pct 范围断言)
- [ ] `tests/test_strategies/test_sma_cross.py:44`: `nunique() >= 1` → `nunique() == 2`
- [ ] `tests/test_backtest/test_engine.py`: `np.random.seed(42)` 固定随机种子
- [ ] `tests/test_backtest/test_metrics.py`: 固定随机种子或使用确定性数据
- [ ] `tests/test_strategies/test_momentum.py:43`: 添加实际信号值断言

## 状态

待开始

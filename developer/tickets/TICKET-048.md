# TICKET-048: get_watchlist_quotes 批量行情查询性能优化

**优先级:** P3 - 低
**状态:** 📋 待开始
**依赖:** TICKET-043
**预计工时:** 1d

## 症状

`get_watchlist_quotes()` 会遍历自选股逐只读取日线缓存、必要时 live fetch，并逐只读取财务数据：

```py
for item in wl.items:
    close_info = store.last_close(code, "daily")
    df = fetcher.daily(code)
    fin = fetcher.financial(code)
```

自选股数量较多时，接口耗时会随股票数线性增长。若缓存缺失，还可能对 akshare 产生多次串行请求。

## 根因分析

接口将“自选列表读取、行情摘要、财务摘要、缓存状态”全部串行拼装在一个循环中，没有批量读取或并发边界。股票名称虽然已尝试批量查询，但行情与财务仍是逐只处理。

## 修复方案

### 1. 明确数据来源优先级

- 默认只从本地 `Store` 读取行情摘要和财务状态
- live fetch 改为显式刷新动作或带上数量/超时限制
- 单只失败不阻塞整组返回

### 2. 增加批量摘要能力

**文件**:

- `src/zhanfa/data/store.py`
- `src/zhanfa/api/services/watchlist_service.py`

考虑新增：

- `Store.last_closes(codes, freq)`
- `Store.date_ranges(codes, freq)`

减少重复文件系统/metadata 读取。

### 3. 补充性能回归测试

使用 mock store/fetcher 验证：

- N 只股票不会触发 N 次 live fetch
- 缓存命中路径调用次数可控
- 单只异常有日志且不影响其他股票

## 验收标准

- [ ] `get_watchlist_quotes()` 在缓存命中时不触发逐只 akshare live fetch
- [ ] 50 只自选股缓存命中场景接口耗时稳定在本地文件读取范围
- [ ] 单只股票数据损坏时返回降级字段并记录日志
- [ ] `uv run pytest tests/test_services/test_watchlist_service.py -q` 通过

## 备注

- 本工单与 `TICKET-043` 有依赖：先补日志，再做性能调整更容易定位回归
- 审查时间: 2026-05-06
- 来源: `developer/auto-code-review/report_full_20260506.md` — 3.2 N+1 查询、P3 路线图第 9 项

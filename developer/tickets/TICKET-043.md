# TICKET-043: API 降级路径静默吞错缺少可观测性

**优先级:** P1 - 高
**状态:** ✅ 已完成
**依赖:** -
**预计工时:** 0.5d

## 症状

`watchlist_service` 与 `data` router 中多处 `except Exception: pass` 会吞掉缓存、数据库、parquet 读取、akshare fallback 等异常。用户只能看到空字段、空列表或缺失状态，服务端日志没有定位线索。

已确认位置：

| 文件 | 行号 | 场景 |
|------|------|------|
| `src/zhanfa/api/routers/data.py` | 50 | `_stock_name()` 读取 stock_list 缓存失败 |
| `src/zhanfa/api/routers/data.py` | 99, 111, 124, 140 | `/api/data/stock-status` 读取日线、财务、分钟、自选归属失败 |
| `src/zhanfa/api/services/watchlist_service.py` | 178, 204 | 批量添加预览读取股票名与其他自选分组失败 |
| `src/zhanfa/api/services/watchlist_service.py` | 274, 325, 344 | 自选股行情读取股票名、日线、财务数据失败 |
| `src/zhanfa/api/services/watchlist_service.py` | 411, 463 | 导出 CSV 读取股票名、补齐 Stock 元信息失败 |

## 根因分析

这些路径多数属于“允许降级”的辅助数据读取，但当前没有结构化日志，也没有区分可忽略的缓存缺失与真正的 I/O、schema、数据库错误。结果是生产问题会被表现为“数据为空”。

## 修复方案

### 1. 增加模块级 logger

**文件**:

- `src/zhanfa/api/routers/data.py`
- `src/zhanfa/api/services/watchlist_service.py`

使用 `logging.getLogger(__name__)`，对可降级异常使用 `logger.warning(..., exc_info=True)` 或 `logger.exception(...)`。

### 2. 区分预期失败与异常失败

- 缓存不存在：不记 error，可按 debug 级别记录
- parquet schema/读取失败：warning，并包含 `code` / `freq` / `path`
- DB 查询失败：exception，并包含业务上下文
- akshare fallback 失败：warning，并保留可读的降级结果

### 3. 补充测试

覆盖至少两个关键路径：

- `/api/data/stock-status` 某个缓存读取失败时仍返回 200，但日志包含异常上下文
- `get_watchlist_quotes()` 某只股票读取失败时不影响其他股票，但日志包含 `code`

## 验收标准

- [x] `src/zhanfa/api/routers/data.py` 不再存在 `except Exception: pass`
- [x] `src/zhanfa/api/services/watchlist_service.py` 不再存在 `except Exception: pass`
- [x] 降级路径返回值保持兼容，不因单只股票失败导致整个接口 500
- [x] 日志包含足够定位信息：接口/函数、股票代码、频率、异常堆栈
- [x] 定向测试通过：`uv run pytest tests/test_api tests/test_services -q`

## 验证结果

- 2026-05-06: 151 tests passed (test_api + test_services)
  - `grep` 确认两个源文件零 `except Exception: pass`
  - 新增 `test_stock_status_corrupted_cache_returns_200_and_logs` — 损坏 parquet 返回 200 + WARNING 日志含 code
  - 新增 `test_partial_failure_logs_code_and_preserves_other_stocks` — 单只股票失败不波及其他 + WARNING 日志含 code
  - 所有现有测试保持通过，接口契约无变化

## 残余风险

- `search_stocks()` 中 akshare fallback (`except Exception: return []`) 未列入工单范围，仍无日志
- 日志级别选择基于工单分类规则，生产环境可能需要根据实际噪声调整

## 备注

- 本工单只处理 API 层可观测性，不改变缓存策略或接口契约
- 审查时间: 2026-05-06
- 来源: `developer/auto-code-review/report_full_20260506.md` — 3.1 静默吞错、P1 路线图第 1 项

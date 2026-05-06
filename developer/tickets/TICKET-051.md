# TICKET-051: 回测请求日期格式统一由后端校验转换

**优先级:** P2 - 中
**状态:** ✅ 已完成
**依赖:** -
**预计工时:** 0.5d

## 症状

代码库同时使用两种日期格式：

- `20200101`: akshare 参数格式
- `2020-01-01`: API/前端常用 ISO 格式

当前转换逻辑分散在：

- `src/zhanfa/api/services/backtest_service.py` 的 `_parse_date()`
- `frontend/src/api/client.ts` 的 `start_date.replace(/-/g, "")` / `end_date.replace(/-/g, "")`

前端需要知道后端内部/akshare 的日期格式，增加了契约耦合。

## 根因分析

API request model 没有承担“外部输入标准化”的职责，导致日期格式转换散落在前后端。后续新增端点或脚本时，容易出现同一字段有时是 ISO、有时是 8 位字符串的问题。

## 修复方案

### 1. 后端 request model 增加日期 validator

**文件**:

- `src/zhanfa/api/models.py`
- `src/zhanfa/api/services/backtest_service.py`

让 API 接收 ISO 日期和 8 位日期，但在后端统一转换为 `date` 或内部标准字符串。服务层不再依赖前端预处理。

### 2. 前端只发送 ISO 日期

**文件**: `frontend/src/api/client.ts`

移除 `replace(/-/g, "")`，前端只按表单语义发送 `YYYY-MM-DD`。

### 3. 覆盖测试

- API 接收 `2020-01-01`
- API 接收 `20200101`
- 非法日期返回 422 或明确 400

## 实施结果

### 后端
- `BacktestRequest` 新增 `field_validator`：接受 ISO `YYYY-MM-DD` 和紧凑 `YYYYMMDD` 两种输入，统一规范化为 `YYYYMMDD`
- 非法格式（如 `2020/01/01`）触发 Pydantic 422 错误

### 前端
- `submitBacktest` 移除 `start_date.replace(/-/g, '')` 和 `end_date.replace(/-/g, '')`
- 前端直接发送 ISO 日期，后端负责格式规范化

### 验收标准

- [x] 回测 API 输入日期由 Pydantic/request model 统一校验
- [x] 前端不再手动替换日期分隔符
- [x] 非法日期有明确错误响应（Pydantic 422）
- [x] `uv run pytest tests/test_api/test_endpoints.py tests/test_services/test_backtest_service.py -v` → 37 passed
- [x] `cd frontend && npm run test` → 153 passed
- [x] `cd frontend && npm run build` → built in 479ms

## 来源

- `developer/auto-code-review/report_full_20260506.md` — 3.3 日期处理的双轨制

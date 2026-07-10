# TICKET-059: 代码审查 Critical/High 后端修复

> 来源：2026-05-07 全量代码审查 | 优先级：P0

## 关联文档

- [审查报告](../auto-code-review/report_full_20260507.md)

## 任务清单

### C0 — Store 路径遍历漏洞
- [x] `src/zhanfa/data/store.py:20-21`: 在 `_path()` 方法中增加路径遍历检测（拒绝含 `..`, `/`, `\` 的 code）
- [x] `src/zhanfa/api/models.py`: 为所有 stock code 字段添加 `Field(pattern=r"^\d{6}$")` 验证
- [x] `src/zhanfa/db/import_data.py:13-18`: `normalize_stock_code()` 非数字输入应抛 `ValueError` 而非透传

### C1 — `_tasks` dict 线程安全
- [x] `src/zhanfa/api/services/backtest_service.py`: 添加 `threading.Lock`，保护 `_tasks` 所有读写操作
- [x] 验证：并发提交回测不出现 `RuntimeError: dictionary changed size during iteration`

### C2 — Task ID 碰撞风险
- [x] `src/zhanfa/api/services/backtest_service.py:124`: `str(uuid.uuid4())[:8]` 改为完整 UUID 或 `uuid.uuid4().hex[:12]`

### C3 — `_strategy_name_for()` N+1 查询
- [x] `src/zhanfa/api/services/backtest_service.py`: `_get_db_history()` 中预先批量查询 strategy_id → name 映射，传入 `_db_row_to_history_item()`

### H1 — 残余 `except Exception: pass`
- [x] `src/zhanfa/api/services/stock_service.py:53`: DB 异常改为 `logger.warning(..., exc_info=True)`
- [x] `src/zhanfa/api/services/stock_service.py:196`: industry comparison 循环内异常同样加日志
- [x] `src/zhanfa/data/store.py:214`: `stats()` 扫描循环内异常同样加日志

### H3 — `initialize` 端点阻塞
- [x] `src/zhanfa/api/routers/data.py:85-90`: 改为 `async def` + `run_in_executor` 或返回 `202 Accepted` + 后台任务

### M1 — Stock code 验证
- [x] 所有 API 端点的 `code` 参数添加 Pydantic 正则验证 `r"^\d{6}$"`

## 验证记录

- `uv run ruff check src/` — 通过
- `uv run mypy src/` — 通过
- `uv run pytest -v` — 327 passed, 231 warnings

## 残余风险

- `vectorbt` 依赖触发 `Pandas4Warning: 'd' is deprecated`，不影响本工单行为。
- 当前工作区仍包含其他工单的既有暂存/未暂存改动，提交前需要按工单拆分变更。

## 状态

已完成

# TICKET-032: API 测试隔离数据库

**优先级:** P1 - 高
**状态:** ✅ 已完成
**依赖:** TICKET-003
**预计工时:** 0.5d

## 症状

`uv run pytest -q` 当前有 API 测试失败：

```text
sqlite3.IntegrityError: UNIQUE constraint failed: strategies.name
```

失败用例: `tests/test_api/test_endpoints.py::test_create_strategy`

## 根因分析

API 测试直接导入生产 app：

```python
from zhanfa.api import app
```

而 `zhanfa.api.__init__` 在导入阶段执行 `init_db()`，默认连接 `sqlite:///data/zhanfa.db`。因此测试会读写本地真实开发数据库，导致：

- 测试依赖本地历史数据，重复运行不幂等
- `test_create_strategy` 创建固定名称 `My Strategy`，第二次运行撞唯一约束
- 测试可能污染开发数据库

## 修复方案

### 1. 为 API 测试提供独立数据库

**文件**:

- `tests/conftest.py`
- `tests/test_api/test_endpoints.py`
- `tests/test_api/test_data.py`

候选方案：

- 在导入 app 前设置 `DATABASE_URL=sqlite:///:memory:` 或临时文件 DB
- 使用 FastAPI dependency override 替换 `get_session`
- 每个测试或每个测试模块创建干净 schema

### 2. 避免 app 导入时产生副作用

**文件**: `src/zhanfa/api/__init__.py`

评估是否将 `init_db()` 从模块导入阶段移动到 lifespan/startup，或提供 app factory：

```python
def create_app() -> FastAPI:
    ...
```

### 3. 修正 API 契约测试

**文件**: `tests/test_api/test_endpoints.py`

`test_watchlist_lifecycle` 当前断言旧字段 `stocks`，真实响应模型返回 `items`。需要更新断言：

```python
assert any(item["code"] == "000001" for item in r.json()["items"])
```

## 验收标准

- [x] 连续执行两次 `uv run pytest -q` 都通过
- [x] 测试不再创建或修改 `data/zhanfa.db`
- [x] API 测试使用隔离数据库，且每次运行状态一致
- [x] watchlist API 测试断言与当前响应模型一致

## 备注

- 审查时间: 2026-05-05
- 当前后端测试结果: 216 passed, 2 failed
- 完成时间: 2026-05-05
- 验证结果: `uv run pytest -q` 通过，220 passed

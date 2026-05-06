# TICKET-044: 移除 FastAPI 模块导入阶段的 init_db 副作用

**优先级:** P1 - 高
**状态:** ✅ 已完成
**依赖:** TICKET-032
**预计工时:** 0.5d

## 症状

`src/zhanfa/api/__init__.py` 在模块顶层执行 `init_db()`：

```py
from zhanfa.db.base import init_db

init_db()
```

任何测试、脚本或工具只要导入 `zhanfa.api`，就会立即连接默认数据库并创建表。此前 `TICKET-032` 已暴露测试会误写 `data/zhanfa.db` 的风险，本问题是该风险的长期根因之一。

## 根因分析

FastAPI app 的创建、数据库初始化、策略注册、调度器启动混在模块导入流程中，导致 import 不再是无副作用操作。测试夹具和命令行工具很难在导入前覆盖数据库 URL 或生命周期。

## 修复方案

### 1. 将 `init_db()` 移入 lifespan

**文件**: `src/zhanfa/api/__init__.py`

在 `lifespan()` 内按顺序执行：

1. `init_db()`
2. `register_strategies()`
3. `_register_scheduler_tasks()`

确保导入模块时不触碰数据库。

### 2. 评估 app factory

如测试仍需要更强隔离，新增 `create_app()`：

- 允许传入 `init_database: bool = True`
- 允许传入 `start_scheduler: bool = True`
- 默认导出 `app = create_app()`

### 3. 补充回归测试

- 导入 `zhanfa.api` 不创建临时数据库文件
- 使用测试数据库启动 TestClient 时只初始化测试库
- scheduler 不在纯 import 时启动后台线程

## 验收标准

- [ ] `src/zhanfa/api/__init__.py` 顶层不再执行 `init_db()`
- [ ] 纯导入 `zhanfa.api` 不产生数据库连接/建表副作用
- [ ] FastAPI 正常启动时仍会初始化数据库并注册策略
- [ ] `uv run pytest tests/test_api -q` 通过

## 备注

- 与 `TICKET-032` 的测试隔离修复相关，但本工单面向生产代码结构
- 审查时间: 2026-05-06
- 来源: `developer/auto-code-review/report_full_20260506.md` — 2.1 后端分层警惕信号、P1 路线图第 2 项

## 验证结果

**完成时间:** 2026-05-06

### 代码变更

1. `src/zhanfa/api/__init__.py`:
   - 移除模块顶层的 `init_db()` 调用
   - `init_db()` 移入 `lifespan()`，在 `register_strategies()` 之前执行
   - 新增 `create_app(init_database=, start_scheduler=)` 工厂函数，方便测试隔离
   - `app = create_app()` 保持默认导出兼容

2. `tests/conftest.py`:
   - `client` fixture 改用 `create_app(init_database=False, start_scheduler=False)` 替代直接导入 `app`
   - 避免测试中启动调度器后台线程

3. `tests/test_api/test_no_import_side_effects.py` (新增):
   - `test_import_zhanfa_api_does_not_create_db_file`: 子进程验证纯导入不创建数据库文件
   - `test_import_zhanfa_api_does_not_start_scheduler_thread`: 子进程验证纯导入不启动调度器线程
   - `test_create_app_no_init_database_no_scheduler`: 验证工厂函数参数控制

### 测试结果

```
tests/test_api/ — 70 passed, 2 warnings
```

### 残余风险

- 无。`zhanfa.db.base` 模块的 `engine` 仍为模块级创建（惰性连接），但这是预期行为 — 仅创建引擎对象不触发文件 I/O。
- 现有测试和 FastAPI 启动流程均验证通过。

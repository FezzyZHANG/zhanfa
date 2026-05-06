# TICKET-016: 去重 ORM 模型定义

| 属性     | 值                              |
| -------- | ------------------------------- |
| 优先级   | P1 - 高                         |
| 依赖     | 003                            |
| 创建日期 | 2026-05-05                      |

## 问题描述

`db/models.py` 和 `api/database.py` 中重复定义了 ORM 模型，使用不同的 `Base` 类：

- `src/zhanfa/db/models.py` — 定义 6 个模型 (`Strategy`, `Stock`, `StockFinancial`, `Watchlist`, `WatchlistItem`, `BacktestResult`)，使用 `zhanfa.db.base.Base`（传统 `declarative_base()`）
- `src/zhanfa/api/database.py` — 重复定义 3 个模型 (`Stock`, `Watchlist`, `WatchlistItem`)，使用本地 `Base(DeclarativeBase)`（SQLAlchemy 2.0 风格）

`watchlist_service.py` 从 `api/database.py` 导入模型，而其他服务从 `db/models.py` 导入，形成两套模型体系。这会导致外键关联异常、迁移冲突和代码维护困难。

此外数据库 URL 被硬编码在 `api/database.py:8`（直接写死 `"sqlite:///data/zhanfa.db"`），而 `config.py:18` 通过环境变量获取。

## 任务清单

- [x] 删除 `api/database.py` 中的重复模型定义（`Stock`, `Watchlist`, `WatchlistItem`）
- [x] 将 `watchlist_service.py` 的导入从 `api/database.py` 改为 `db/models.py`
- [x] 验证两套模型之间无字段差异，如有差异需合并
- [x] 删除 `api/database.py` 中硬编码的数据库 URL，统一使用 `config.py` 获取
- [x] 确保所有其他模块的导入一致指向 `db/models.py`
- [x] 运行现有测试确认无回归

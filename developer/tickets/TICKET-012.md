# TICKET-012: 补充缺失的后端 API 端点

| 属性     | 值                              |
| -------- | ------------------------------- |
| 优先级   | P1 - 高                         |
| 依赖     | 003                            |
| 创建日期 | 2026-05-05                      |

## 问题描述

前端调用了两个后端不存在的 API 端点：

1. `GET /api/stocks/industry/{industry}/comparison` — 前端 `client.ts:196` 调用，用于获取同行业公司对比数据
2. `GET /api/backtest/compare?ids=...` — 前端 `client.ts:253` 调用，用于对比多个回测结果

这两个端点在后端路由中都找不到对应的处理函数。

此外，数据库模型存在重复定义问题：
- `src/zhanfa/db/models.py` 中定义了一套 SQLAlchemy ORM 模型 (`Strategy`, `Stock`, `StockFinancial`, `Watchlist`, `WatchlistItem`, `BacktestResult`)
- `src/zhanfa/api/database.py` 中又定义了一套重复的模型 (`Stock`, `Watchlist`, `WatchlistItem`)，使用不同的 `Base` 类
- `watchlist_service.py` 从 `api/database.py` 导入，而其他服务从 `db/models.py` 导入，造成两套模型体系

数据库 URL 也被硬编码在两处：
- `src/zhanfa/config.py:19` — 使用 `os.getenv("DATABASE_URL", ...)`
- `src/zhanfa/api/database.py:8` — 直接写死 `"sqlite:///data/zhanfa.db"`

## 任务清单

- [x] 在 `src/zhanfa/api/routers/stocks.py` 中实现 `GET /stocks/industry/{industry}/comparison` 端点
- [x] 在 `src/zhanfa/api/routers/backtest.py` 中实现 `GET /backtest/compare` 端点
- [x] 删除 `src/zhanfa/api/database.py` 中的重复模型定义，统一使用 `db/models.py` 的模型
- [x] 更新 `watchlist_service.py` 的导入指向 `db/models.py`
- [x] 统一数据库 URL 的来源，所有模块通过 `config.py` 获取

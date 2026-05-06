# TICKET-002: 后端 API 服务设计

**优先级:** P0 - 紧急
**状态:** ✅ 已完成
**依赖:** 无
**预计工时:** 设计 1d + 开发 3d

## 需求描述

将现有 Python 函数调用转换为 RESTful API 服务，为前端提供数据。最大化复用现有 `src/zhanfa/` 模块代码。

## API 端点设计

### 策略/流派

| 方法   | 路径                          | 说明                          |
| ------ | ----------------------------- | ----------------------------- |
| GET    | `/api/strategies`             | 列出所有策略，支持 ?category= |
| GET    | `/api/strategies/{id}`        | 策略详情 + 参数 schema        |
| GET    | `/api/strategies/{id}/results`| 该策略的历史回测结果列表      |
| POST   | `/api/strategies`             | 新建自定义策略                |
| PUT    | `/api/strategies/{id}`        | 更新策略参数                  |

### 股票数据

| 方法 | 路径                                  | 说明                              |
| ---- | ------------------------------------- | --------------------------------- |
| GET  | `/api/stocks`                         | 股票列表，支持 ?industry=&page=   |
| GET  | `/api/stocks/{code}`                  | 股票元信息 + 最新财务摘要         |
| GET  | `/api/stocks/{code}/daily`            | K 线数据 ?start=&end=&freq=       |
| GET  | `/api/stocks/{code}/financial`        | 历史财报 ?years=3                 |
| GET  | `/api/stocks/{code}/indicators`       | 技术指标 (SMA/MACD/RSI 等)        |

### 自选股

| 方法   | 路径                                  | 说明                |
| ------ | ------------------------------------- | ------------------- |
| GET    | `/api/watchlists`                     | 用户的自选股分组列表 |
| POST   | `/api/watchlists`                     | 创建新分组          |
| GET    | `/api/watchlists/{id}`                | 分组详情 + 股票列表 |
| POST   | `/api/watchlists/{id}/items`          | 添加股票到分组      |
| DELETE | `/api/watchlists/{id}/items/{code}`   | 从分组移除股票      |

### 回测

| 方法 | 路径                         | 说明                              |
| ---- | ---------------------------- | --------------------------------- |
| POST | `/api/backtest/run`          | 提交回测任务，返回 task_id        |
| GET  | `/api/backtest/{task_id}`    | 查询回测状态 & 结果               |
| GET  | `/api/backtest/history`      | 历史回测记录                      |

### 调度

| 方法 | 路径                      | 说明               |
| ---- | ------------------------- | ------------------ |
| GET  | `/api/scheduler/status`   | 当前调度状态       |
| POST | `/api/scheduler/trigger`  | 手动触发数据更新   |

## 技术选型

| 层级      | 选择                     | 理由                          |
| --------- | ------------------------ | ----------------------------- |
| Web 框架  | FastAPI                  | 异步、自动 OpenAPI、生态好    |
| 数据校验  | Pydantic v2              | 与 FastAPI 深度集成           |
| ORM       | SQLAlchemy 2.0           | 异步支持、成熟稳定            |
| 异步任务  | ARQ (Async Redis Queue)  | 轻量，适合回测这种 CPU 密集型 |
| 迁移      | Alembic                  | SQLAlchemy 标准搭配           |
| 认证(可选)| JWT (python-jose)        | 如需多用户                    |

## 对现有代码的复用

```python
# 直接 import，无需改造
from zhanfa.data import Fetcher, Store, Pipeline
from zhanfa.strategies import BaseStrategy
from zhanfa.backtest import run_backtest, compute_metrics, generate_report
from zhanfa.config import Config
```

## 验收标准

- [x] FastAPI 服务启动，`/docs` 可访问 Swagger UI
- [x] 所有 API 端点实现并返回正确的 Pydantic schema
- [x] 与现有 parquet 缓存兼容，不破坏 CLI 使用
- [x] 回测任务异步执行（长时间运行不阻塞 HTTP）
- [x] 单元测试覆盖所有端点

## 备注

- API 服务与现有 CLI 脚本共存：启动服务后 `uv run uvicorn zhanfa.api:app`，日常脚本依然使用 CLI
- K 线数据量较大（每只股票数年日线），考虑分页和日期范围过滤

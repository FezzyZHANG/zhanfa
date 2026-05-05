# 自动化模块

定时调度与工作流编排，用于数据更新、成分股刷新等周期性任务。

## 调度器架构

### 技术基础

基于 [schedule](https://github.com/dbader/schedule) 库（v1.2.2）的轻量级封装。schedule 是纯 Python 的单进程调度器，运行时轮询当前时间并与已注册的作业时间比较，触发到期作业。无守护进程、无外部依赖。

### Scheduler 类

`zhanfa.automation.scheduler.Scheduler` — 核心调度器，提供：

| 特性 | 说明 |
|------|------|
| `daily(time_str)` | 装饰器，每日指定时间执行（如 `"17:00"`） |
| `hourly()` | 装饰器，每小时执行 |
| `run_loop(interval=60)` | 阻塞式主循环，每 N 秒检查一次到期作业 |
| `run_pending()` | 单次非阻塞执行 — 只运行当前到期的作业后立即返回 |
| `stop()` | 优雅停止循环 |
| `list_jobs()` | 列出已注册的作业列表 |
| `state_file` | 可选 JSON 文件路径，用于作业列表持久化 |
| `on_error` | 可选错误通知回调 `Callable[[str, Exception], None]` |

作业注册通过 Python 装饰器完成，装饰时内部调用 `schedule.every().day.at(...)` 或 `schedule.every().hour`。

```python
from zhanfa.automation.scheduler import Scheduler

scheduler = Scheduler(
    state_file="data/schedule.json",
    on_error=lambda job, exc: print(f"[ALERT] {job} failed: {exc}"),
)

@scheduler.daily("17:00")
def update_data():
    update_daily_data()        # 来自 workflows 模块

@scheduler.hourly()
def health_check():
    print("alive")

scheduler.run_loop()  # 主进程阻塞运行
```

### 持久化与通知

**状态持久化**: 构造时传入 `state_file` 参数后，每次注册/取消作业时自动将作业列表写入 JSON 文件。启动时自动加载并恢复（仅恢复作业元信息：函数名、时间、类型；不自动重新绑定装饰器注册的函数 — 需在启动脚本中重新执行装饰器代码以重建 schedule 规则）。

**错误通知**: 通过 `on_error` 回调将异常传递给外部系统。调度器本身不内置邮件/Slack/钉钉等通知渠道，需由调用方在回调中自行实现。

## 工作流

`zhanfa.automation.workflows` 模块，两个主要工作流函数：

### update_daily_data

每日数据更新：批量拉取最新日线 K 线数据并写入 parquet 缓存。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `codes` | `list[str] \| None` | `None` | 要更新的股票代码。`None` 则从已有缓存中获取代码列表 |
| `discover_new` | `bool` | `True` | 是否扫描全 A 股市场，自动发现未缓存的新上市股票 |
| `max_new` | `int` | `50` | 每次最多新增的股票数，防止首次运行拉取全部市场数据 |

返回: `{"updated": int, "failed": int, "new_discovered": int, "details": {...}}`

### weekly_index_rebalance

每周指数调仓对比：获取指数最新成分股列表，与上一期快照对比，记录调入/调出变更。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `index_code` | `str` | `"000300"` | 指数代码，默认沪深 300 |

返回: `{"index_code": str, "current_count": int, "previous_count": int, "added": list, "removed": list, "current": list}`

调仓快照以 `rebalance_{index_code}` 和 `rebalance_{index_code}_prev` 两个 key 保存在 meta parquet 分区中。

## API 端点

`/api/scheduler` 路由提供两个端点：

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/api/scheduler/status` | 返回已注册作业列表及运行状态 |
| `POST` | `/api/scheduler/trigger` | 手动触发工作流，body: `{"action": "update_daily \| rebalance_index", "codes": [...], "index_code": "..."}` |

## 如何添加新的定时作业

1. 在 `workflows.py`（或你自建模块）中编写任务函数：

```python
def my_new_job():
    # 任务逻辑 ...
    return {"status": "ok"}
```

2. 在启动脚本中用装饰器注册：

```python
@scheduler.daily("09:30")
def run_my_job():
    my_new_job()
```

3. 如需从 API 手动触发，在 `api/routers/scheduler.py` 的 `trigger` 端点中添加对应的 action 分支。

## 当前限制

> **诚实声明**: 以下功能已在 `Scheduler` 类中实现接口，但模块级默认实例和 API 集成中尚未启用。这些限制将在 TICKET-014 后续阶段解决。

| 限制 | 详情 | 影响 |
|------|------|------|
| **默认实例无持久化** | `scheduler.py` 底部创建的模块级 `scheduler` 实例未传入 `state_file`，也未传入 `on_error`。API 路由器使用该实例，因此作业列表在进程重启后丢失 | 生产部署时必须自行创建带 `state_file` 的 Scheduler 实例 |
| **API 无后台循环** | `/status` 返回 `running=False` 硬编码 — API 进程中没有运行 `run_loop()`。目前调度器和 API 是分离的：调度器在独立进程中通过 `python -c "..."` 或自定义入口脚本运行 | 不能通过 API 启停调度循环 |
| **工作流为骨架代码** | `update_daily_data` 是顺序单线程拉取，无并发和重试机制；`weekly_index_rebalance` 仅记录变更而不触发调仓信号或通知 | 适合少量股票（<100）的日常使用，海量全市场更新需进一步优化 |
| **无内置通知** | `on_error` 回调是通用接口，不内置任何具体通知渠道 | 使用者需自行实现邮件/钉钉/企业微信等通知 |

### 与文档描述的差异

`docs/architecture.md` 中的 `Scheduler` 描述展示了 `state_file` 和 `on_error` 等接口 — 这些接口已在代码中实现，但**默认实例未配置**。创建自己的 `Scheduler(state_file=..., on_error=...)` 实例即可获得完整功能。

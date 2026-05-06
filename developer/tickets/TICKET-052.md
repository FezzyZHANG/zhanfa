# TICKET-052: 调度时间配置与实际注册值对齐

**优先级:** P2 - 中
**状态:** ✅ 已完成
**依赖:** TICKET-041
**预计工时:** 0.5d

## 症状

`src/zhanfa/config.py` 中存在：

```py
update_hour: int = 17
```

但当前 FastAPI lifespan 注册调度任务时写死了：

- 日线更新: `15:30`
- 分钟线更新: `15:45`
- 指数调仓: `16:00`

配置值与实际行为不一致，运维或开发者看到 `update_hour` 时会误判任务执行时间。

## 根因分析

调度器从早期单一“每日更新小时”演进为多个任务时间点，但配置层没有同步升级。结果是 `Config` 中保留了半废弃字段，而实际注册逻辑直接硬编码字符串。

## 修复方案

### 1. 重构 Config 调度配置

**文件**:

- `src/zhanfa/config.py`
- `src/zhanfa/api/__init__.py`

将 `update_hour` 替换或扩展为明确字段：

- `daily_update_time`
- `minute_update_time`
- `weekly_rebalance_time`

允许环境变量覆盖。

### 2. 注册任务读取 Config

`_register_scheduler_tasks()` 从 `config` 读取时间，不再硬编码。

### 3. 文档同步

更新 `developer/environment.md` 或对应环境变量文档，说明调度时间配置。

## 实施结果

### config.py
- 移除 `update_hour: int = 17` 半废弃字段
- 新增 `daily_update_time` / `minute_update_time` / `weekly_rebalance_time` 三个明确字段
- 对应环境变量: `SCHEDULE_DAILY_UPDATE` (默认 `15:30`), `SCHEDULE_MINUTE_UPDATE` (默认 `15:45`), `SCHEDULE_WEEKLY_REBALANCE` (默认 `16:00`)

### api/__init__.py
- `_register_scheduler_tasks()` 从 `config` 读取任务时间，不再硬编码

## 验收标准

- [x] 调度注册不再写死 `15:30` / `15:45` / `16:00`
- [x] `Config` 中不再保留语义模糊的半废弃 `update_hour`
- [x] 环境变量能覆盖调度时间 (`SCHEDULE_*` 系列)
- [x] `/api/scheduler/status` 展示的任务时间与配置一致
- [x] `uv run pytest tests/test_api/test_endpoints.py tests/test_api/test_data.py -v` → 38 passed

## 来源

- `developer/auto-code-review/report_full_20260506.md` — 3.4 Config 类的半废弃、P2 路线图第 6/7 项

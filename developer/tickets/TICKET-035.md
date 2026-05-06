# TICKET-035: 数据刷新 freq 参数被忽略

**优先级:** P2 - 中
**状态:** ✅ 已完成
**依赖:** TICKET-028, TICKET-029
**预计工时:** 0.5d

## 症状

`POST /api/data/refresh` 接收 `freq` 参数，但实际刷新逻辑始终调用 `update_daily_data()`，只会拉取日线：

```python
result = update_daily_data(...)
```

当 `force=true` 且 `freq=minute_15` / `minute_30` / `minute_60` 时，会先删除对应分钟级缓存，再调用日线刷新，导致分钟级缓存被清空但没有补回。

## 根因分析

TICKET-028 已要求 refresh API 支持分钟级 `freq`，但当前实现只在删除缓存时使用了 `body.freq`，刷新工作流没有按频率分派。

## 修复方案

### 1. 增加分钟级刷新工作流

**文件**: `src/zhanfa/automation/workflows.py`

新增类似函数：

```python
def update_minute_data(codes: list[str], period: str) -> dict:
    ...
```

功能：

- `minute_60` -> `Fetcher.minute(code, period="60")`
- `minute_30` -> `Fetcher.minute(code, period="30")`
- `minute_15` -> `Fetcher.minute(code, period="15")`
- 返回结构与 `update_daily_data()` 保持一致

### 2. refresh 路由按 freq 分派

**文件**: `src/zhanfa/api/routers/data.py`

根据 `body.freq` 选择 daily 或 minute 工作流。未知 `freq` 返回 400，而不是静默走 daily。

### 3. 补充测试

**文件**: `tests/test_api/test_data.py`

新增测试：

- `freq="minute_15"` 调用 `Fetcher.minute(period="15")`
- `force=true` 删除的是目标频率缓存，并重新拉取目标频率
- 非法 `freq` 返回 400

## 验收标准

- [x] `POST /api/data/refresh` 支持 `daily`、`minute_60`、`minute_30`、`minute_15`
- [x] 分钟级强制刷新不会误拉日线数据
- [x] 非法频率返回明确错误
- [x] `uv run pytest tests/test_api/test_data.py -q` 通过

## 备注

- 审查时间: 2026-05-05
- 与 `scripts/fetch_minute.py` 的频率命名需保持一致

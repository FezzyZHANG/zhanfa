# TICKET-045: Pydantic 模型可变默认值统一改为 default_factory

**优先级:** P1 - 高
**状态:** ✅ 已完成
**依赖:** -
**预计工时:** 0.5d

## 症状

`src/zhanfa/api/models.py` 中多个 Pydantic 字段直接使用 `{}`、`[]` 或模型实例作为默认值。其中 `StockDataStatus.minute_60/minute_30/minute_15` 使用 `MinuteCacheStatus()` 作为默认对象：

```py
minute_60: MinuteCacheStatus = MinuteCacheStatus()
minute_30: MinuteCacheStatus = MinuteCacheStatus()
minute_15: MinuteCacheStatus = MinuteCacheStatus()
```

同文件还存在多处可变默认值：

| 行号 | 字段 |
|------|------|
| 24, 38, 239 | `params: dict[str, Any] = {}` |
| 133, 163, 309, 368, 390 | `list[...] = []` |
| 310, 327 | `dict[...] = {}` |

## 根因分析

Pydantic 对可变默认值有一定保护，但直接使用可变对象会让模型行为依赖 Pydantic 版本细节，也会触发静态检查与代码审查风险。模型实例默认值尤其不直观，后续迁移 Pydantic 版本时更容易引入共享状态或序列化差异。

## 修复方案

**文件**: `src/zhanfa/api/models.py`

统一改为 `Field(default_factory=...)`：

```py
params: dict[str, Any] = Field(default_factory=dict)
items: list[WatchlistItemDetail] = Field(default_factory=list)
minute_60: MinuteCacheStatus = Field(default_factory=MinuteCacheStatus)
```

## 验收标准

- [ ] `src/zhanfa/api/models.py` 不再出现 API 模型字段级 `= {}` / `= []` / `= SomeModel()`
- [ ] `StockDataStatus()` 的三个分钟状态对象彼此独立
- [ ] 现有 API 响应 JSON 字段保持兼容
- [ ] `uv run pytest tests/test_api -q` 通过

## 备注

- 本工单仅清理 API schema 默认值，不调整业务返回字段
- 审查时间: 2026-05-06
- 来源: `developer/auto-code-review/report_full_20260506.md` — 4.3 MinuteCacheStatus 默认值问题、P1 路线图第 3 项

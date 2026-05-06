# TICKET-028: 前端图表 + API 支持分钟级数据 (1h/15min/30min)

**优先级:** P1 - 高
**状态:** ✅ 已完成
**依赖:** TICKET-027 (已完成), [Fetcher.minute()](src/zhanfa/data/fetcher.py)
**预计工时:** 1d

## 需求描述

前端图表现仅支持日/周/月/季/年级别（从日线客户端聚合）。需要新增 1h/15min/30min 三种分钟级频率，数据从后端分钟级 API 获取。

## 任务清单

### 1. 前端类型扩展

**文件**: `frontend/src/types/index.ts`

- `Freq` 类型扩展为 `'D' | 'W' | 'M' | 'Q' | 'Y' | '60min' | '30min' | '15min'`
- 新增 `FREQ_MINUTE` 常量集 `['60min', '30min', '15min']` 用于区分"服务端获取"vs"客户端聚合"

### 2. ChartToolbar UI

**文件**: `frontend/src/components/chart/ChartToolbar.tsx`

- 新增分钟级频率按钮组（1h/30min/15min），与日/周/月按钮组视觉分离
- 选择分钟级频率时，周/月/季/年按钮置灰（不可同时选）
- 反之亦然：选择日线频率时分钟按钮置灰

### 3. 数据获取适配

**文件**: `frontend/src/hooks/useStocks.ts` (或类似)

- 当前所有数据从日线客户端聚合。需新增逻辑：
  - 若 `freq` 属于 `FREQ_MINUTE`，调用新 API（见下）直接获取服务端分钟数据
  - 若 `freq` 属于日线聚合（D/W/M/Q/Y），保持现有逻辑不变

### 4. 后端 API — 分钟级 K 线端点

**文件**: `src/zhanfa/api/routers/data.py`

新增端点 `GET /api/data/kline?code=000001&freq=60min`:

```python
@router.get("/kline")
def get_kline(code: str, freq: str = "daily"):
    fetcher = Fetcher()
    if freq in ("15min", "30min", "60min", "1h"):
        # 映射: 1h → 60
        period = "60" if freq == "1h" else freq.replace("min", "")
        df = fetcher.minute(code, period=period)
    else:
        df = fetcher.daily(code)
    return df.reset_index().to_dict(orient="records")
```

### 5. 后端 stock-status 适配

**文件**: `src/zhanfa/api/routers/data.py`

`GET /api/data/stock-status` 当前硬编码检查 `store.exists(code, "daily")`。扩展为同时检查 `minute_60`、`minute_15`、`minute_30`：

```json
{
  "daily": {"exists": true, "rows": 5000, "start": "2010-01-04", "end": "2026-05-05"},
  "minute_60": {"exists": true, "rows": 1970, "start": "2024-04-18", "end": "2026-04-30"},
  "minute_15": {"exists": true, "rows": 1970, "start": "2025-10-28", "end": "2026-04-30"}
}
```

### 6. refresh API 适配

**文件**: `src/zhanfa/api/routers/data.py`

`POST /api/data/refresh` 当前 `freq` 参数默认 `"daily"`。扩展支持 `"minute_60"`、`"minute_15"`、`"minute_30"`，调用 `fetcher.minute(code, period=...)`。

## 验收标准

- [x] `Freq` 类型包含 `'60min' | '30min' | '15min'`
- [x] ChartToolbar 显示分钟级频率按钮
- [x] 分钟级频率和日线聚合频率互斥
- [x] 选择 1h 时图表展示 ~2 年的小时级 K 线
- [x] 选择 15min 时图表展示 ~6 个月的 15 分钟 K 线
- [x] `GET /api/data/kline?freq=60min` 返回正确数据
- [x] `GET /api/data/stock-status` 返回分钟级缓存状态
- [x] `POST /api/data/refresh` 支持分钟级 freq
- [x] 图表加载状态和空状态正常
- [x] TypeScript 编译通过 (`npx tsc --noEmit`)

# TICKET-058: 修复 CI lint 错误（后端 ruff + 前端 ESLint）

| 字段 | 值 |
|------|-----|
| 优先级 | P1 - 高 |
| 状态 | ✅ 已完成 |
| 依赖 | - |
| 关联 | TICKET-047 (StockInfo 前后端对齐，该 import 可能因未完成而闲置) |

## 背景

GitHub Actions CI 在 `push` / `pull_request` 触发时，后端 `ruff check` 和前端 `eslint` 均报错导致流水线失败。

- **后端**: `uv run ruff check src/` → 28 errors（本地）/ 21 errors（CI），18 个可自动修复
- **前端**: `npm run lint` → 30 problems（28 errors, 2 warnings）

该问题阻塞所有 PR 的 CI 绿灯。

## 问题分析

### 后端 — ruff (28 errors)

#### 类别 A：未使用的导入 F401（约 13 处，ruff --fix 可自动修复）

| 文件 | 未使用导入 |
|------|-----------|
| `src/zhanfa/api/models.py:8` | `pydantic.Field` |
| `src/zhanfa/api/routers/scheduler.py:7` | `update_minute_data` |
| `src/zhanfa/api/routers/stocks.py:3` | `StockInfo`（注：TICKET-047 可能重新引入） |
| `src/zhanfa/api/routers/watchlists.py:7` | `BatchPreviewResponse` |
| `src/zhanfa/api/services/backtest_service.py:13` | `pandas` |
| `src/zhanfa/api/services/strategy_service.py:149-153` | `MACDStrategy`, `LowPEStrategy`, `PEGStrategy`, `TrendFundamental`, `MomentumLowVol`（5 个） |
| `src/zhanfa/config.py:5` | `pathlib.Path` |
| `src/zhanfa/db/base.py:4` | `sqlalchemy.orm.Session` |
| `src/zhanfa/strategies/composite/momentum_lowvol.py:3` | `numpy` |
| `src/zhanfa/strategies/trend/turtle.py:6` | `atr` |

#### 类别 B：导入不在文件顶部 E402（7 处，需手动修复）

文件 `src/zhanfa/api/routers/data.py` — `logger = logging.getLogger(__name__)` 位于标准库 import 之后、项目 import 之前，导致后续 7 个 import 语句违反 E402。

**根因**: logger 初始化被放在 import 块中间。

**修复**: 将 `logger = logging.getLogger(__name__)` 移到所有 import 之后。

#### 类别 C：未定义名称 F821（1 处，需手动修复）

文件 `src/zhanfa/api/services/watchlist_service.py:240` — 函数签名使用 `"Store"` 字符串注解，但文件顶部未导入 `Store`。由于文件有 `from __future__ import annotations`，注解不会在运行时求值，但 ruff 仍然报错。

**修复**: 在文件顶部添加 `from typing import TYPE_CHECKING` + `if TYPE_CHECKING: from zhanfa.data.store import Store`，或在顶部直接导入 `Store`。

#### 类别 D：未使用变量 F841（2 处，需手动修复或 --unsafe-fixes）

文件 `src/zhanfa/jq/adapter.py:114-115` — `has_rsi` 和 `has_ma` 变量赋值后从未使用。第 123 行的条件分支隐式覆盖了 RSI/MA 逻辑，直接检查 `"period" in params`。

**修复**: 如果 `has_rsi`/`has_ma` 是残留调试变量，直接删除；如果是未完成的逻辑分支，补充使用或标记为 `_has_rsi` / `_has_ma`。

### 前端 — ESLint (28 errors, 2 warnings)

#### 类别 A：组件在 render 内创建 react-hooks/static-components（10 errors）

文件 `frontend/src/components/data/StockDataTable.tsx:92-95` — `SortIcon` 组件在 `StockDataTable` 渲染函数内部定义，每次渲染都会创建新组件实例，导致状态重置。

**修复**: 将 `SortIcon` 提取为文件级组件，通过 props 接收 `sortKey` 和 `sortAsc`。

#### 类别 B：render 期间访问 ref react-hooks/refs（4 errors × 2 = 8 errors）

文件 `frontend/src/pages/stock/StockDetailPage.tsx`:
- `chartContainerRef.current?.clientWidth`（line 139）传递给 `ChartCrosshair`
- `timeScaleRef.current`（lines 160, 178）传递给 `IndicatorPane`

**根因**: ref.current 在渲染期间读取，React 19 严格模式下会报错。这些值应该通过 state 或直接传 undefined 让子组件自行测量。

**修复**:
- `containerWidth`: 使用 `useState` + `ResizeObserver` 或直接传 `undefined`
- `mainTimeScale`: 通过 state 存储，在 `onTimeScaleReady` 回调中 `setMainTimeScale`

#### 类别 C：useEffect 缺少依赖 react-hooks/exhaustive-deps（1 warning）

文件 `frontend/src/components/chart/KlineChart.tsx:353` — `ref` 在 useEffect 内使用但未列入依赖数组。`ref` 是 `externalRef || internalRef` 的稳定引用，可安全加入 deps。

#### 类别 D：useMemo 依赖不稳定 react-hooks/exhaustive-deps（1 warning）

文件 `frontend/src/pages/strategies/StrategiesPage.tsx:21-37` — `strategies` 变量在三元表达式 `Array.isArray(strategiesData) ? ... : []` 中计算，导致每次渲染生成新数组引用，使 useMemo 失效。

**修复**: 将三元表达式移入 useMemo 回调内部，或对 `strategies` 使用独立 useMemo。

## 任务清单

### 后端
- [x] 移除所有未使用的导入（可直接 `ruff check --fix src/`）
- [x] 修复 `data.py` 导入顺序：将 `logger = logging.getLogger(__name__)` 移至所有 import 之后
- [x] 修复 `watchlist_service.py` F821：导入 `Store`（TYPE_CHECKING 或顶层导入）
- [x] 处理 `jq/adapter.py` F841：删除或补充 `has_rsi`/`has_ma` 变量逻辑
- [x] 验证 `ruff check src/` 零错误

### 前端
- [x] 提取 `StockDataTable.tsx` 的 `SortIcon` 为文件级组件
- [x] 修复 `StockDetailPage.tsx` render 期间 ref 访问：`containerWidth` 和 `mainTimeScale` 改用 state
- [x] 修复 `KlineChart.tsx` useEffect 缺少 `ref` 依赖
- [x] 修复 `StrategiesPage.tsx` useMemo 依赖不稳定
- [x] 验证 `npm run lint` 零错误

### 额外修复（初次 lint 通过后暴露的更多错误）
- [x] 修复 `WatchlistTable.tsx` — 提取 `SortHeader` 为文件级组件
- [x] 修复 `AddStockDialog.tsx` — 将 effect 内 setState 改为 handleClose 回调
- [x] 修复 `useWatchlistUrlFilters.ts` — 替换 `as any` 为明确类型
- [x] 修复 `utils.test.ts` — 添加 eslint-disable 注释处理故意常量表达式

### 收尾
- [x] 验证 `npm run test` 通过
- [x] 验证 `npm run build` 通过
- [x] 验证 `uv run pytest -v` 通过
- [x] 更新 `developer/README.md` 工单状态

## 验证结果

- [x] `uv run ruff check src/` → All checks passed!
- [x] `cd frontend && npm run lint` → 0 errors, 0 warnings
- [x] `cd frontend && npm run test` → 10 test files, 153 tests passed
- [x] `cd frontend && npm run build` → built in 652ms
- [x] `uv run pytest -v` → 300 passed, 2 skipped

## 验证标准

1. `uv run ruff check src/` 零错误
2. `cd frontend && npm run lint` 零错误零警告
3. GitHub Actions CI 全绿

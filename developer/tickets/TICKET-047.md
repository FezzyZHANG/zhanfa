# TICKET-047: StockInfo 前后端契约对齐

**优先级:** P2 - 中
**状态:** ✅ 已完成
**依赖:** -
**预计工时:** 0.5d

## 症状

后端 `StockInfo` 只定义并返回：

```py
class StockInfo(BaseModel):
    code: str
    name: str
```

但前端 `frontend/src/types/index.ts` 中的 `StockInfo` 要求：

```ts
export interface StockInfo {
  code: string;
  name: string;
  exchange: string;
  industry: string;
  market_cap: number;
  listed_date: string;
}
```

真实 API 模式下，`fetchStocks()` 返回的数据不满足前端类型契约。当前前端可能依赖 mock 数据掩盖问题，或在页面渲染时得到 `undefined` 字段。

## 根因分析

股票列表接口早期只面向搜索/选择场景，前端类型随后扩展为完整股票元信息，但后端 schema 与服务层 `list_stocks()` 没有同步补齐字段，也没有单独拆分轻量列表类型与详情类型。

## 修复方案

### 方案 A: 后端补齐字段

**文件**:

- `src/zhanfa/api/models.py`
- `src/zhanfa/api/services/stock_service.py`

从数据库或 akshare 元数据中补齐 `exchange`、`industry`、`market_cap`、`listed_date`。无法可靠获取时给出明确的 `None`/空值契约，并在前端类型中体现可选。

### 方案 B: 前端拆分类型

**文件**:

- `frontend/src/types/index.ts`
- `frontend/src/api/client.ts`

拆分 `StockListItem` 与 `StockInfo`，列表接口只要求 `code` / `name`，详情页再使用完整类型。

## 实施结果

### 后端变更
- `StockInfo` Pydantic 模型新增 `exchange`/`industry`/`market_cap`/`listed_date` 可选字段 (默认 None)
- `get_stock_meta` 新增 DB 查表逻辑：存在时回填完整元信息，DB 不可用时静默降级为 None

### 前端变更
- `StockInfo` 接口字段改为可选 (`exchange?`, `industry?`, `market_cap?`, `listed_date?`)
- `fetchStock` 不再硬编码空值，直接透传 API 响应
- `StockDetailPage` 适配可选字段：exchange/industry 空值回退显示 `--`，market_cap 空值回退 `0`

### 验收标准

- [x] OpenAPI schema 与 `frontend/src/types/index.ts` 对 `StockInfo` 字段要求一致
- [x] `fetchStocks()` 的真实 API 返回值满足前端编译期类型 (`tsc -b` 通过)
- [x] mock 数据与真实 API 字段结构一致（mock 已含全部字段，optional 兼容）
- [x] `uv run pytest tests/test_api/test_endpoints.py tests/test_services/ -v` → 122 passed
- [x] `cd frontend && npm run build` → built in 511ms
- [x] `cd frontend && npm run test` → 153 passed

## 备注

- 优先选择能保持页面语义清晰的方案；若列表页不需要完整元数据，拆分类型更稳
- 审查时间: 2026-05-06
- 来源: `developer/auto-code-review/report_full_20260506.md` — 2.2 StockInfo 契约不一致、4.2 fetchStock 硬填字段

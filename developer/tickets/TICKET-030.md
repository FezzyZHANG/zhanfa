# TICKET-030: 数据初始化缺失导致自选添加股票与数据管理页面不可用

**优先级:** P0 - 紧急
**状态:** ✅ 已完成
**依赖:** -
**预计工时:** 0.5d

## 症状

1. **自选股 — 添加股票不可用**: 在 `/watchlist` 页面点击"+ 添加股票"，搜索能看到结果，但点击"添加"后操作失败（后端返回 500 或静默失败）。
2. **数据管理页面无数据**: `/data` 页面显示全部为 0（缓存 0 只股票、DB 0 条记录等）。
3. **数据管理页面抓取按钮（部分场景）不可用**: 网速慢或 akshare 超时时，stats 加载处于 pending 状态导致按钮 disabled。

## 根因分析

### 根因 1: `stocks` 表从未被填充

`WatchlistItem.code` 和 `StockFinancial.code` 都有外键约束指向 `stocks.code` ([models.py:102](../../src/zhanfa/db/models.py#L102)):

```python
code = Column(String(10), ForeignKey("stocks.code"), nullable=False)
```

`import_stocks()` 函数 ([import_data.py:13](../../src/zhanfa/db/import_data.py#L13)) 可以从 `meta/stock_list.parquet` 导入股票元信息到 `stocks` 表，但**从未被自动调用**。它只存在于文档示例和测试中。

### 根因 2: `update_daily_data()` 不填充 `stocks` 表

`POST /api/data/refresh` → `update_daily_data()` ([workflows.py:13](../../src/zhanfa/automation/workflows.py#L13)) 会：
- 调用 `fetcher.stock_list()` 获取全 A 股列表（为了发现新股票）
- 调用 `fetcher.daily()` 拉取日线数据并缓存到 parquet

但**从不调用 `import_stocks()` 将股票写入 `stocks` 表**。所以即使执行了数据刷新，`stocks` 表始终为空。

### 根因 3: `add_item()` 未校验/自动创建 Stock 记录

`add_item()` ([watchlist_service.py:70](../../src/zhanfa/api/services/watchlist_service.py#L70)) 直接创建 `WatchlistItem(code=code)` 而不检查 `stocks` 表中是否存在该代码。SQLite 外键约束（已启用 `PRAGMA foreign_keys=ON`）会拒绝插入，导致 500 错误。

### 调用链

```
用户点击"添加股票"
  → AddStockDialog 搜索 (searchStocks API)
    → search_stocks() → Stock 表为空 → fallback akshare → 返回结果 ✓
  → 用户确认添加
    → POST /api/watchlists/:id/items
      → add_item() → WatchlistItem(code=code)
        → SQLite FK constraint FAILS (stock not in stocks table) ✗
```

## 修复方案

### 方案 A: 数据刷新时自动导入（推荐）

在 `update_daily_data()` 中，发现新股票或拉取成功后，调用 `import_stocks()` 将股票元信息写入 `stocks` 表。

**变更点:**
- [src/zhanfa/automation/workflows.py](../../src/zhanfa/automation/workflows.py#L13): `update_daily_data()` 末尾调用 `import_stocks()`
- [src/zhanfa/api/services/watchlist_service.py](../../src/zhanfa/api/services/watchlist_service.py#L70): `add_item()` / `batch_add_items()` 中先 `_ensure_stock()` 再插入

**优点:** 最小改动，数据刷新自动完成初始化。  
**缺点:** 首次刷新需要同时拉取股票列表和日线数据，耗时较长。

### 方案 B: 添加股票时自动创建 Stock 记录

仅在 `add_item()` / `batch_add_items()` 中自动创建缺失的 `Stock` 记录（从 akshare 获取名称）。

**优点:** 改动更小，不影响数据刷新流程。  
**缺点:** `stocks` 表只有用户添加过的股票，数据管理页面仍然看不到全市场数据。

### 建议

采用**方案 A**，同时在数据管理页面增加"初始化数据"引导：
- 首次进入 `/data` 页面时，如检测到 `stocks` 表为空且缓存为空，显示引导提示"点击开始初始化数据"
- 数据刷新完成后自动填充 `stocks` 表，自选添加功能立即可用

## 涉及文件

| 文件 | 改动 |
|------|------|
| [src/zhanfa/automation/workflows.py](../../src/zhanfa/automation/workflows.py) | `update_daily_data()` 中调用 `import_stocks()` 填充 DB |
| [src/zhanfa/api/services/watchlist_service.py](../../src/zhanfa/api/services/watchlist_service.py) | `add_item()` / `batch_add_items()` 防御性创建 Stock |
| [src/zhanfa/db/import_data.py](../../src/zhanfa/db/import_data.py) | 可选：增加 `import_stocks_from_list()` 内存列表导入（不依赖 parquet） |
| [frontend/src/pages/DataPage.tsx](../../frontend/src/pages/DataPage.tsx) | 增加空状态引导提示 |

## 验收标准

- [x] 全新部署（空 DB + 空缓存）后，在数据管理页面点击"抓取至今"，刷新完成后 `stocks` 表自动填充
- [x] 自选股搜索和添加功能可用，不报 FK 错误
- [x] `GET /api/data/stats` 返回非零数据
- [x] Swagger `/docs` 中 `POST /api/watchlists/{id}/items` 测试通过
- [x] 已有数据的环境不受影响（幂等）

## 备注

- 与 TICKET-024（数据管理 API）、TICKET-026（自选增强）直接相关
- FK 约束在 SQLite WAL 模式下通过 `PRAGMA foreign_keys=ON` 强制执行
- `stock_list.parquet` 由 `Fetcher.stock_list()` 首次调用时自动缓存，无需单独生成
- 完成时间: 2026-05-05
- 验证结果: `uv run pytest -q` 通过，224 passed；`npm run build` 与 `npm run test` 通过

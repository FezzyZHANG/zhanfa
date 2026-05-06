# TICKET-026: 增强自选股管理

**优先级:** P2 - 中
**状态:** ✅ 已完成
**依赖:** 024 (可选，用于数据状态标记)
**预计工时:** 0.75d

## 需求描述

当前自选股管理（[WatchlistPage](../../frontend/src/pages/watchlist/WatchlistPage.tsx) + [watchlist_service](../../src/zhanfa/api/services/watchlist_service.py)）已支持多分组、CRUD、批量添加/移动、行情查看、CSV 导出。但存在以下不足：

1. **缺少数据状态感知** — 用户不知道自选股是否有日线/财务数据缓存
2. **行情刷新慢** — `watchlist_service.get_quotes()` 逐只调用 akshare（N 次 HTTP），没有批量和缓存复用
3. **批量操作体验一般** — 批量添加缺少预览确认，移动操作需要多步
4. **缺少排序/筛选** — 表格不支持多列排序和按条件筛选（如 PE < 20, ROE > 15%）

## 功能清单

### 1. 自选股数据状态标记

在每个自选股行显示数据可用性图标：
- 🟢 有日线 + 财务数据
- 🟡 仅有日线
- 🔴 无缓存数据
- 悬浮显示详情：日线覆盖日期范围、财务报告期数

数据来源：调用 TICKET-024 的 `GET /api/data/stock-status` 或在 watchlist quotes 接口中附带 data_status 字段。

在前端 [WatchlistTable](../../frontend/src/components/watchlist/WatchlistTable.tsx) 和 [WatchlistCards](../../frontend/src/components/watchlist/WatchlistCards.tsx) 中增加数据状态列/标记。

### 2. 行情批量加载优化

后端 [watchlist_service.get_quotes()](../../src/zhanfa/api/services/watchlist_service.py) 改进：
- 优先从已缓存的 parquet 读取最后一日收盘价（O(1) 文件读取），而非逐只调 akshare
- 仅对缓存未覆盖的股票调用 `Fetcher.daily()` 实时拉取
- 返回结果中增加 `data_freshness` 字段（缓存日期 vs 实时）

预期效果：100 只自选股的行情查询从 ~30s 降到 <2s。

### 3. 筛选与排序增强

在 [WatchlistTable](../../frontend/src/components/watchlist/WatchlistTable.tsx) 增加：
- **列头点击排序**: 代码、名称、价格、涨跌幅、PE、PB、股息率（当前仅支持部分列）
- **快速筛选**: PE 范围、涨跌幅阈值、行业过滤
- **搜索框**: 在表内按代码/名称过滤（当前搜索仅在添加弹窗中）

筛选状态保存到 URL search params，支持分享和浏览器前进/后退。

### 4. 批量操作改进

- **批量添加预览**: 粘贴代码列表后，先展示匹配结果表格（代码、名称、是否已在其他分组），确认后再添加
- **批量删除确认**: 显示将删除的股票列表，二次确认
- **拖拽移动** (可选): 在侧边栏拖拽股票到目标分组

### 5. 自选股一键刷新数据

在每个分组的操作栏增加"刷新数据"按钮：
- 调用 `POST /api/data/refresh`（TICKET-024），codes 限定为该分组内股票
- 显示迷你进度条

## 验收标准

- [ ] 自选股表格每行显示数据可用性状态图标
- [ ] 行情加载时间（100 只股票）< 3s
- [ ] 表格支持多列排序和 PE/涨跌幅筛选
- [ ] 批量添加有预览确认步骤
- [ ] "刷新数据"按钮可触发分组内股票的数据更新
- [ ] 筛选参数反映在 URL search params 中
- [ ] 不影响现有自选股 CRUD 功能

## 备注

- 数据状态标记与 TICKET-024 解耦：TICKET-024 未完成时，可在 watchlist quotes 接口中附带简化的 data_status
- 行情优化依赖 parquet 缓存读取，代码变更集中在 [watchlist_service.py](../../src/zhanfa/api/services/watchlist_service.py)
- 拖拽移动为可选特性，优先级低于筛选排序

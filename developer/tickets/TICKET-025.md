# TICKET-025: 数据管理前端页面

**优先级:** P1 - 高
**状态:** ✅ 已完成
**依赖:** 024
**预计工时:** 1d

## 需求描述

用户需要一个集中的数据管理页面来了解系统数据状态并执行数据操作。目前没有页面能回答"我有哪些数据""数据到哪一天了""还需要拉哪些数据"等问题。

页面路由: `/data`，在导航栏中增加入口。

## 功能清单

### 1. 数据概览仪表盘

页面顶部展示核心统计卡片：

| 卡片 | 内容 |
|------|------|
| 日线缓存 | 已缓存股票数 / 全市场股票数，总数据行数，存储大小 |
| 数据覆盖 | 最早日期 ~ 最新日期，覆盖交易日数 |
| 财务数据 | 已缓存财务数据股票数，报告期范围 |
| 数据库 | stocks / financial / watchlist / strategies / backtest 各表记录数 |

使用现有 UI 组件 [Card](../../frontend/src/components/ui/Card.tsx)，样式参考 [BacktestMetrics](../../frontend/src/components/backtest/BacktestMetrics.tsx) 的卡片网格布局。

### 2. 抓取至今按钮

- **位置**: 页面顶部操作栏，醒目位置
- **行为**: 
  - 点击后弹出确认对话框，显示将刷新的股票数量
  - 可选项: "仅增量更新"（默认）/ "强制全量刷新"
  - 提交后显示进度（成功/失败计数、进度条）
  - 完成后刷新页面统计
- **实现**: 调用 `POST /api/data/refresh`，轮询 `/api/scheduler/status` 获取进度

当用户选择了"强制全量刷新"时，按钮文案变为"⚠️ 强制全量刷新"以示警告。

### 3. 数据覆盖日历视图

以热力图或日历图展示数据覆盖情况：
- X 轴 = 日期（月/周粒度），Y 轴 = 股票（可选前 N 只）
- 有数据的格子绿色，无数据灰色
- 可选替代: 简化为柱状图——每天有多少只股票有数据

使用 ECharts 日历热力图（项目已依赖 echarts）。

### 4. 股票数据详情表

可搜索、可排序的表格，每行显示：
- 代码、名称、是否在自选股、日线数据范围、日线行数、财务数据范围、财务行数

支持按"数据最旧""数据最新""缺少财务数据"等条件筛选。

点击行可跳转到 `/stock/$code`。

### 5. 路由与导航

在 [router.ts](../../frontend/src/router.ts) 添加 `/data` 路由，在 [Navbar](../../frontend/src/components/Navbar.tsx) 添加"数据管理"导航项。

### 6. API Client 扩展

在 [client.ts](../../frontend/src/api/client.ts) 添加：
- `fetchDataStats()` → `GET /api/data/stats`
- `fetchStockDataStatus(code)` → `GET /api/data/stock-status?code=`
- `refreshData(params)` → `POST /api/data/refresh`

类型定义添加到 [types/index.ts](../../frontend/src/types/index.ts)。

## 验收标准

- [ ] `/data` 页面可访问，导航栏有入口
- [ ] 统计卡片正确展示缓存和数据库状态
- [ ] "抓取至今"按钮可触发刷新，有进度反馈
- [ ] 数据覆盖图正常渲染（即使缓存为空）
- [ ] 股票详情表可搜索、可排序
- [ ] 点击股票行跳转到股票详情页
- [ ] 页面响应式布局，在 1024px 宽度下正常显示
- [ ] Mock 数据覆盖开发场景（`VITE_ENABLE_MOCK=true`）

## 备注

- 数据覆盖日历在股票数 > 100 时降级为柱状图（性能考虑）
- 刷新进度轮询间隔 5 秒，超时 10 分钟自动停止
- 页面默认不自动刷新统计，用户需手动点击刷新按钮或"抓取至今"后自动刷新

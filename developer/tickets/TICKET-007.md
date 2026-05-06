# TICKET-007: 自选股票数据库与看板

**优先级:** P1 - 高
**状态:** ✅ 已完成
**依赖:** 001, 003
**预计工时:** 2d

## 需求描述

提供用户自选股票管理功能，支持多分组、快速查看分组内股票的核心行情指标，点击进入个股详情。

## 功能清单

### 分组管理

- [x] 创建/重命名/删除自选分组
- [x] 默认分组："默认"（不可删除）
- [x] 分组列表侧栏，显示每个分组的股票数量

### 股票管理

- [x] 添加股票到分组（按代码搜索）
- [x] 从分组移除股票
- [ ] 拖拽排序（可选）
- [x] 添加备注（如"海龟策略入选"）

### 看板视图

- [x] 表格视图：代码 | 名称 | 最新价 | 涨跌幅 | PE | PB | 股息率 | 备注
- [x] 卡片视图：每只股票一个卡片，显示迷你 K 线缩略图（sparkline）
- [x] 排序：按涨跌幅/PE/市值等列排序
- [x] 点击行/卡片跳转到个股详情页
- [x] 定频刷新（手动刷新按钮）

### 批量操作

- [x] 批量添加（粘贴代码列表）
- [x] 批量移动到其他分组
- [x] 导出分组为 CSV

## 技术方案

```typescript
interface Watchlist {
  id: number;
  name: string;
  item_count: number;
  items: WatchlistItem[];
}

interface WatchlistItem {
  code: string;
  name: string;
  added_at: string;
  notes: string;
  // 实时行情（加载时注入）
  latest_price?: number;
  change_pct?: number;
  pe?: number;
  pb?: number;
  dividend_yield?: number;
}
```

数据流：
1. 页面加载 → 获取分组列表
2. 选中分组 → 获取 items + 批量查询最新行情
3. 定时间隔 30s 刷新行情（仅刷新当前选中分组）

## 组件拆分

```
components/watchlist/
├── WatchlistPage.tsx       # 主页面 (侧栏分组 + 主内容区)
├── WatchlistSidebar.tsx    # 分组列表侧栏
├── WatchlistTable.tsx      # 表格视图
├── WatchlistCards.tsx      # 卡片视图 (含 sparkline)
├── AddStockDialog.tsx      # 添加股票弹窗 (搜索)
├── GroupDialog.tsx         # 创建/重命名分组弹窗
└── useWatchlist.ts         # 数据获取 & 刷新 hook
```

## 验收标准

- [x] 分组 CRUD 全部正常
- [x] 添加/移除股票即时生效
- [x] 看板实时显示最新行情数据
- [x] 表格排序正常（数值列按大小，名称列按字母）
- [x] 搜索股票时支持代码和名称模糊匹配
- [x] 点击股票跳转到 `/stock/{code}` 正常
- [x] 导出 CSV 内容正确

## 备注

- 行情实时性：akshare 数据有延迟，标注数据更新时间。如需实时行情需要额外接入 WebSocket 行情源（如新浪/腾讯/东方财富的免费推送）。
- 迷你 K 线 sparkline 可复用 TradingView Lightweight Charts 的极小配置实例，或用纯 SVG/CSS 实现简单折线。

# TICKET-001: 前端技术选型与架构设计

**优先级:** P0 - 紧急
**状态:** ✅ 已完成
**依赖:** 无
**预计工时:** 调研 1d + 搭建 2d

## 需求描述

为 zhanfa 设计并搭建前端项目骨架，用于浏览不同交易流派（趋势/动量/基本面/多因子）的详细信息，以及访问自选股票数据库查看财报分析和 K 线图。

## 功能范围

### 核心页面

1. **流派列表页** — 按分类（趋势跟踪/动量/基本面/复合）展示所有策略卡片
2. **流派详情页** — 单个策略的描述、参数、历史回测表现、关联股票
3. **自选股看板** — 用户自选股票列表，支持添加/删除/分组
4. **个股详情页** — K 线图 + 技术指标 + 财报数据可视化
5. **回测结果页** — 回测绩效指标卡片 + 净值曲线 + 交易记录

### 技术选型

| 层级       | 选择                         | 替代方案               |
| ---------- | ---------------------------- | ---------------------- |
| 框架       | React 18 + TypeScript        | Vue 3 / Svelte         |
| 构建       | Vite                         | Next.js / Turbopack    |
| UI 组件    | shadcn/ui + Tailwind CSS     | Ant Design / Mantine   |
| K 线图     | TradingView Lightweight Charts | ECharts / D3         |
| 财报图表   | ECharts (react-echarts)      | Recharts / Nivo        |
| 状态管理   | TanStack Query + Zustand     | Redux Toolkit / Jotai  |
| 路由       | TanStack Router              | React Router v6        |
| 表格       | TanStack Table               | AG Grid Community      |

### 项目结构

```
frontend/
├── src/
│   ├── components/
│   │   ├── ui/          # shadcn/ui 基础组件
│   │   ├── chart/       # KlineChart, FinancialChart
│   │   └── strategy/    # StrategyCard, StrategyList
│   ├── pages/
│   │   ├── strategies/  # 流派列表 & 详情
│   │   ├── watchlist/   # 自选股看板
│   │   ├── stock/       # 个股详情 (K线+财报)
│   │   └── backtest/    # 回测结果
│   ├── hooks/           # useStocks, useStrategy, useBacktest
│   ├── api/             # axios/fetch 封装
│   ├── types/           # TypeScript 类型定义
│   └── lib/             # 工具函数
├── public/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── tailwind.config.ts
```

## 验收标准

- [ ] `npm run dev` 可启动前端开发服务器
- [ ] 路由系统正常工作，5 个页面骨架渲染
- [ ] 与后端 API 交互的 hooks 封装完成（可用 mock 数据）
- [ ] TypeScript 严格模式通过，类型覆盖完整
- [ ] shadcn/ui 主题配置完成

## 备注

- 如果团队只有 Python 开发者，可考虑 Streamlit 作为快速替代方案（放弃灵活性和性能，换取零前端成本）。本方案假设我们追求专业金融 UI 体验。
- TradingView Lightweight Charts 是免费且功能完整的，不需要 TradingView 付费许可。

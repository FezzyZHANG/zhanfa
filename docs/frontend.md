# 前端文档

战法 (zhanfa) 前端 —— 量化策略研究平台 Web UI。

## 技术栈

| 层 | 工具 | 用途 |
|---|---|---|
| 框架 | React 19 + TypeScript 6 | UI 框架与类型安全 |
| 构建 | Vite 8 | 开发服务器与生产构建 |
| 样式 | Tailwind CSS 4 | 原子化 CSS |
| 路由 | @tanstack/react-router v1 | 文件系统风格路由 |
| 状态 | @tanstack/react-query v5 | 服务端状态管理 |
| 状态 | zustand | 客户端状态管理 |
| 图表 | lightweight-charts 5 | K 线图（TradingView 风格） |
| 图表 | ECharts 6 + echarts-for-react | 财务图表、回测可视化 |
| 请求 | axios | HTTP 客户端 |

## 目录结构

```
frontend/
├── .env                    # 环境变量 (VITE_ENABLE_MOCK)
├── vite.config.ts          # Vite 构建配置 + 自定义文档插件
├── vitest.config.ts        # Vitest 测试配置
├── tsconfig.json           # TS 项目引用
├── tsconfig.app.json       # 应用 TS 配置 (路径别名 @/)
├── eslint.config.js        # ESLint flat config
├── index.html              # Vite 入口 HTML
├── package.json
└── src/
    ├── main.tsx            # 入口: React StrictMode
    ├── App.tsx             # 根组件: QueryClientProvider + RouterProvider
    ├── router.ts           # 路由定义
    ├── index.css           # Tailwind CSS 导入 + Markdown 样式
    ├── api/
    │   ├── client.ts       # API 客户端 (所有数据抓取函数 + USE_MOCK 守卫)
    │   └── mock.ts         # 完整 Mock 数据集
    ├── components/
    │   ├── Layout.tsx      # 布局外壳 (Navbar + Outlet)
    │   ├── Navbar.tsx      # 顶部导航栏
    │   ├── backtest/       # 回测组件 (表单/指标/图表/对比)
    │   ├── chart/          # K 线图与指标面板
    │   ├── financial/      # 财务分析组件 (9 个图表/表格)
    │   ├── strategy/       # 策略卡片与参数编辑
    │   ├── watchlist/      # 自选股组件 (表格/卡片/侧边栏)
    │   └── ui/             # 基础 UI 组件 (Button/Card/Badge/Skeleton)
    ├── hooks/              # React Query hooks (数据获取与变更)
    ├── lib/
    │   ├── utils.ts        # 工具函数 (格式化)
    │   ├── indicators.ts   # 技术指标计算 (SMA/EMA/MACD/RSI/Bollinger/Donchian)
    │   └── docs.ts         # 文档加载器
    ├── pages/              # 页面组件 (backtest/docs/stock/strategies/watchlist)
    └── types/
        └── index.ts        # 所有 TypeScript 类型定义
```

## 路由结构

| 路径 | 页面组件 | 说明 |
|---|---|---|
| `/` | StrategiesPage | 策略列表（首页） |
| `/strategies` | StrategiesPage | 策略列表 |
| `/strategies/$strategyId` | StrategyDetailPage | 策略详情 + 参数编辑 + 回测 |
| `/watchlist` | WatchlistPage | 自选股看板 |
| `/stock/$stockCode` | StockDetailPage | 个股详情（K 线 + 指标 + 财务） |
| `/backtest` | BacktestPage | 回测主页（表单 + 历史列表 + 对比） |
| `/backtest/$backtestId` | BacktestDetailPage | 回测详情（完整指标） |
| `/docs?file=` | DocsPage | 文档阅读（Markdown 渲染） |
| `/data` | DataPage | 数据管理（统计、覆盖图、刷新） |

路由使用 `@tanstack/react-router` v1 的 `createRootRoute` / `createRoute` API。`Layout` 组件作为根路由包裹所有页面，内含 `Navbar` 导航栏。

## 核心页面

### 策略浏览 (/strategies)

展示所有注册策略的卡片列表，支持按类别筛选（趋势跟踪 / 动量 / 基本面 / 复合策略）。点击卡片进入策略详情页。

### 策略详情 (/strategies/$strategyId)

展示策略描述、回测参数编辑器、历史回测记录列表。可直接提交回测任务。

### 自选股看板 (/watchlist)

管理自选股分组，支持表格视图和卡片视图切换。每一行/卡片显示最新价格、涨跌幅、PE、PB、股息率及**数据缓存状态**（🟢日线+财务/🟡仅日线/🔴无缓存）。支持按代码/名称搜索、PE 范围筛选、涨跌方向过滤，列头点击排序，筛选参数反映在 URL search params 中。批量添加含预览确认（显示已在其他分组的股票），支持勾选批量删除。每个分组有一键刷新数据按钮（调用 `/api/data/refresh`）。

### 个股详情 (/stock/$stockCode)

K 线图（TradingView lightweight-charts）+ 技术指标面板（MACD / RSI）+ 财务分析（ROE、利润率、估值等图表）。工具栏支持周期切换（日/周/月/季/年）和指标开关。

### 回测 (/backtest, /backtest/$backtestId)

回测主页面：参数表单 + 历史回测列表 + 多策略对比视图。回测详情页包含净值曲线、回撤曲线、年度/月度收益热力图、交易记录表等完整可视化。

### 数据管理 (/data)

展示缓存和数据库状态概览仪表盘。顶部统计卡片显示日线缓存覆盖率、数据日期范围、财务数据量、数据库各表记录数。支持数据覆盖柱状图（按年），以及股票数据详情表格（可搜索/排序/筛选）。

"抓取至今"按钮触发数据刷新，支持增量更新和强制全量刷新两种模式，带确认对话框和进度反馈。

### 文档 (/docs)

渲染 `docs/` 和 `developer/` 目录下的 Markdown 文件，通过自定义 Vite 插件 (`virtual:docs`) 在构建时读取，支持 GFM 格式。

## Mock 模式

前端支持两种运行模式，由环境变量 `VITE_ENABLE_MOCK` 控制：

| 模式 | `VITE_ENABLE_MOCK` | 行为 |
|---|---|---|
| 真实 API | `false` | 通过 Vite 代理转发 `/api/*` 到 `localhost:8000` |
| Mock | `true` | 使用 `src/api/mock.ts` 中的硬编码合成数据 |

切换方式：修改 `frontend/.env` 文件中的 `VITE_ENABLE_MOCK`，重启开发服务器即可。

Mock 数据包含：
- 8 个预定义策略（双均线交叉、海龟交易、RSI 超买超卖、MACD 金叉死叉、低市盈率价值、PEG 策略、趋势+基本面共振、动量+低波多因子）
- 4 只股票（贵州茅台、五粮液、宁德时代、招商银行），含 5 年财务数据
- 3 个自选股分组，含行情报价
- 2 个模拟回测结果

## 开发流程

```bash
# 安装依赖
cd frontend
npm install

# 启动开发服务器（默认 http://localhost:5173）
npm run dev

# 类型检查
tsc -b

# 构建生产版本
npm run build

# 预览生产构建
npm run preview
```

开发服务器配置了以下代理：
- `/api` → `http://localhost:8000`（Python FastAPI 后端）

需要先启动后端（`uv run uvicorn zhanfa.api:app --reload`）或将 `VITE_ENABLE_MOCK` 设为 `true`。

### 添加新页面

1. 在 `src/pages/<name>/` 下创建页面组件
2. 在 `src/router.ts` 中添加路由定义
3. 如需数据，在 `src/hooks/` 中添加 React Query hook，在 `src/api/client.ts` 中添加 API 函数并实现对应的 Mock 返回

## 组件说明

### 基础 UI 组件 (`src/components/ui/`)

- **Button** — 按钮（default / outline / ghost / destructive 变体）
- **Card** — 卡片容器（CardHeader / CardTitle / CardDescription / CardContent）
- **Badge** — 标签徽章
- **Skeleton** — 骨架屏加载占位

### 图表组件 (`src/components/chart/`)

- **KlineChart** — 基于 lightweight-charts 的 K 线图，支持十字光标
- **IndicatorPane** — 技术指标面板（MACD 柱状图 + RSI 线）
- **ChartToolbar** — 图表工具栏（频率切换、指标显隐开关）
- **FinancialChart** — 通用财务图表封装（基于 ECharts）

### 财务组件 (`src/components/financial/`)

- **MetricCards** — 关键指标卡片（PE / PB / ROE / 股息率等）
- **RevenueProfitChart** — 营收与利润趋势图
- **ROEChart** — ROE 变化趋势
- **MarginChart** — 毛利率/净利率趋势
- **DebtRatioChart** — 资产负债率趋势
- **ValuationChart** — PE/PB 估值走势
- **IndustryRadar** — 行业对比雷达图
- **FinancialTable** — 财务数据明细表格
- **FinancialPanel** — 财务面板容器，组合上述子组件

### 回测组件 (`src/components/backtest/`)

- **BacktestForm** — 回测参数表单（策略选择、股票代码、日期范围、参数覆盖）
- **BacktestMetrics** — 绩效指标卡片（收益率、夏普比率、最大回撤等）
- **EquityCurve** — 净值曲线图
- **DrawdownCurve** — 回撤曲线图
- **MonthlyHeatmap** — 月度收益热力图
- **YearlyReturns** — 年度收益柱状图
- **TradeTable** — 交易记录表格
- **CompareView** — 多策略对比视图

## 技术指标计算

`src/lib/indicators.ts` 实现了常用技术指标，全部为纯函数，不依赖外部数据源：

| 函数 | 指标 | 参数 |
|---|---|---|
| `calcSMA(closes, period)` | 简单移动平均 | `period` |
| `calcEMA(closes, period)` | 指数移动平均 | `period` |
| `calcMACD(closes, fast, slow, signal)` | MACD 金叉死叉 | `(12, 26, 9)` |
| `calcRSI(closes, period)` | 相对强弱指数 | `14` |
| `calcBollinger(closes, period, stdDev)` | 布林带 | `(20, 2)` |
| `calcDonchian(highs, lows, period)` | 唐奇安通道 | `20` |

## Mock 数据与真实 API 对照

每个 API 函数在 `src/api/client.ts` 中都遵循统一的 Mock 模式：

```typescript
export async function fetchSomeData(param: string) {
  if (USE_MOCK) {
    const data = getMockSomeData(param);
    return delay(data, 300);
  }
  const { data } = await api.get('/api/some-endpoint', { params: { param } });
  return data;
}
```

Mock 数据文件 `src/api/mock.ts` 中的辅助函数可生成完整的模拟净值曲线、回撤曲线、年度/月度收益数据。

## 测试

前端使用 Vitest + jsdom 进行测试。

### 运行测试

```bash
cd frontend
npm run test           # 单次运行
npx vitest             # 监听模式（开发时使用）
```

### 测试配置

`vitest.config.ts` 中配置了：
- **环境**: `jsdom` — 模拟浏览器 DOM，支持组件渲染测试
- **全局 API**: `true` — `describe`/`it`/`expect` 可直接使用
- **路径别名**: `@` → `src/` — 与 Vite 保持一致

### 测试文件结构

```
src/
├── lib/__tests__/
│   ├── utils.test.ts          # 工具函数测试（格式化、类别映射）
│   └── indicators.test.ts     # 技术指标计算测试（SMA/EMA/MACD/RSI/Bollinger/Donchian）
├── api/__tests__/
│   └── client.test.ts         # API 客户端测试（Mock axios，验证请求路径与参数）
└── components/__tests__/
    ├── ui.test.tsx             # 基础 UI 组件渲染测试（Button/Badge/Card/Skeleton）
    └── StrategyCard.test.tsx   # 策略卡片组件测试
```

### 测试类别

| 类别 | 覆盖内容 | 工具 |
|---|---|---|
| 工具函数 | `cn`, `formatCurrency`, `formatPercent`, `formatNumber`, `formatDate`, `getCategoryLabel`, `getCategoryColor` | 纯函数断言 |
| 技术指标 | `calcSMA`, `calcEMA`, `calcMACD`, `calcRSI`, `calcBollinger`, `calcDonchian` | 合成 K 线数据计算验证 |
| API 客户端 | 策略/股票/K线/财务/自选股/回测 的 HTTP 请求路径与参数 | `vi.mock('axios')` |
| UI 组件 | Button 变体/尺寸、Badge 变体、Card 子组件组合、Skeleton | `@testing-library/react` |
| 业务组件 | StrategyCard 渲染（名称/描述/类别标签/参数徽章）、点击事件 | `@testing-library/react` |

### CI 集成

GitHub Actions 的 `ci.yml` 中已配置 `frontend` job：`npm ci` → `npm run lint` → `npm run test` → `npm run build`。

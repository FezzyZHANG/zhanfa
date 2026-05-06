# TICKET-004: K 线图表组件

**优先级:** P1 - 高
**状态:** ✅ 已完成
**依赖:** 001, 003
**预计工时:** 3d

## 需求描述

实现交互式 K 线图组件，支持主流技术指标叠加、时间范围缩放、十字光标等金融图表标准交互。

## 功能清单

### 基础功能
- [x] OHLCV 蜡烛图渲染
- [x] 成交量柱状图（与 K 线联动缩放）
- [x] 时间范围拖拽缩放 / 滚轮缩放
- [x] 十字光标 — 悬浮显示当日 OHLCV 数据
- [x] 支持日/周/月/季/年 频率切换

### 技术指标叠加
- [x] MA 均线 (SMA/EMA，可配置周期和颜色)
- [x] MACD 副图 (DIF/DEA/柱)
- [x] RSI 副图
- [x] 布林带 (BOLL) 叠加
- [x] 唐奇安通道 (Donchian) — 海龟策略专用

### 交互
- [x] 点击某日 K 线 → 在侧栏显示当日详细数据
- [x] 指标显示/隐藏切换
- [x] 多股票对比模式（叠加收盘价折线）

### 数据加载
- [x] 日期范围选择器 → 按需请求 `/api/stocks/{code}/daily?start=&end=`
- [x] 首次加载默认显示最近 1 年日线
- [x] 加载状态和错误处理

## 技术方案

```typescript
// 使用 TradingView Lightweight Charts
import { createChart, CrosshairMode, LineStyle } from 'lightweight-charts';

// 封装的组件接口
interface KlineChartProps {
  code: string;              // 股票代码
  freq?: 'D' | 'W' | 'M';   // 频率
  indicators?: Indicator[];  // 要显示的技术指标
  onDateClick?: (date: string) => void;
}
```

## 组件拆分

```
components/chart/
├── KlineChart.tsx         # 主 K 线组件
├── VolumeChart.tsx        # 成交量副图
├── IndicatorPane.tsx      # 技术指标副图 (MACD/RSI)
├── ChartToolbar.tsx       # 频率切换、指标开关
├── ChartCrosshair.tsx     # 十字光标信息浮层
└── useChartData.ts        # 数据获取 hook
```

## 验收标准

- [x] 输入股票代码，K 线图正确渲染最近 1 年日线数据
- [x] 滚轮缩放、拖拽平移流畅（>30fps）
- [x] 技术指标叠加计算正确（与同花顺/东方财富对比验证）
- [x] 多频率切换（日/周/月）正常
- [x] 无数据或加载失败时显示友好提示

## 实施记录

**完成日期:** 2026-05-05

### 新增文件
- `frontend/src/lib/indicators.ts` — 技术指标计算 (SMA/EMA/MACD/RSI/Bollinger/Donchian)
- `frontend/src/hooks/useChartData.ts` — 图表数据 hook，含频率聚合和指标计算
- `frontend/src/components/chart/ChartToolbar.tsx` — 频率切换 + 指标开关工具栏
- `frontend/src/components/chart/ChartCrosshair.tsx` — 十字光标 OHLCV 浮层
- `frontend/src/components/chart/IndicatorPane.tsx` — MACD/RSI 副图组件

### 修改文件
- `frontend/src/types/index.ts` — 新增 Freq、IndicatorConfig、DateRange 类型
- `frontend/src/api/client.ts` — fix fetchKline 对接 `/api/stocks/{code}/daily`
- `frontend/src/api/mock.ts` — getKlineData 支持 start/end 日期过滤
- `frontend/src/hooks/useStocks.ts` — useKline 支持 start/end 参数
- `frontend/src/components/chart/KlineChart.tsx` — 完整重写，支持所有指标叠加、十字光标、多股票对比
- `frontend/src/pages/stock/StockDetailPage.tsx` — 集成所有图表组件

### 技术实现
- 使用 lightweight-charts v5 Canvas 渲染，滚轮缩放/拖拽由库原生支持
- 频率转换在前端聚合（日→周/月/季/年）减少 API 请求
- MA 均线覆盖 SMA5/10/20/60 + EMA12/26，可配置颜色和线型
- MACD/RSI 使用独立 chart 实例 + timeScale 同步实现副图联动
- 唐奇安通道支持海龟策略可视化

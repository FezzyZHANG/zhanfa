# TICKET-060: 代码审查 Critical/High 前端修复

> 来源：2026-05-07 全量代码审查 | 优先级：P0

## 关联文档

- [审查报告](../auto-code-review/report_full_20260507.md)

## 任务清单

### C4 — `navigate()` 在 render body 中调用 (BacktestPage)
- [x] `frontend/src/pages/backtest/BacktestPage.tsx:34-36`: 将 `navigate()` 移入 `useEffect`
  ```typescript
  useEffect(() => {
    if (pollResult?.status === 'done' && taskId) {
      navigate({ to: '/backtest/$backtestId', params: { backtestId: String(pollResult.id) } });
    }
  }, [pollResult, taskId, navigate]);
  ```

### C5 — KlineChart crosshair handler 过期闭包
- [x] `frontend/src/components/chart/KlineChart.tsx:151-160`: 用 `useRef` 保持 `data` 和 `onCrosshairMove` 引用最新
- [x] 验证：切换频率后 crosshair 使用最新 `dataRef` 查找 OHLCV，避免读取旧频率数组

### H7 — `useBacktest` 仅发送第一只股票
- [x] `frontend/src/hooks/useBacktest.ts:23`: 改为发送全部 `stock_codes` 或限制 UI 为单选
- [x] 若后端不支持多股回测，更新 `BacktestForm` UI 为单选并更新类型签名

### M2 — `useChartData` 类型断言不安全
- [x] `frontend/src/hooks/useChartData.ts:96`: `indicators: null as unknown as ChartIndicatorResults` 改为 `ChartIndicatorResults | null`
- [x] 所有消费 `indicators` 的组件增加判空保护

### H — 缺少 React Error Boundary
- [x] `frontend/src/App.tsx`: 添加顶层 `ErrorBoundary` 组件
- [x] 为 KlineChart、IndicatorPane、EquityCurve 等图表组件添加独立的 Error Boundary

### H — API 请求无 AbortController
- [x] `frontend/src/api/client.ts`: 为 fetch 类请求添加 AbortSignal 支持
- [x] 各 hooks 在组件卸载时取消未完成的请求

## 状态

✅ 已完成

## 实现记录

- 将 `BacktestPage` 完成态导航移入 `useEffect`。
- `KlineChart` 使用 ref 保存最新 `data`、`onCrosshairMove` 和 `onDateClick`，订阅回调不再捕获旧数据。
- 后端当前只支持单标的 `code`，因此 `BacktestForm` 改为单选标的，`useBacktestSubmit` 类型签名改为 `stock_code`。
- `useChartData` 的 `indicators` 改为 `ChartIndicatorResults | null`，股票详情页在渲染 K 线和指标副图前显式判空。
- 新增通用 `ErrorBoundary`，并在应用顶层、K 线图、MACD/RSI 指标副图、回测净值曲线处接入。
- API 客户端支持可选 `AbortSignal`；React Query hooks 透传 `signal`，`DataPage` 手动状态查询使用 `AbortController`。

## 验证

- `npm run lint` ✅
- `npm run build` ✅（沙箱内因原生依赖/子进程 EPERM 失败，授权沙箱外重跑通过；仍有既有 Vite chunk size warning）
- `npm run test` ✅（11 files / 161 tests；仍有 DataPage 测试既有 `act(...)` warning）

## 文档同步

- 已更新 `docs/frontend.md`：单标的回测表单、API AbortSignal、顶层 ErrorBoundary。
- 已更新 `developer/architecture.md`：前端错误边界、请求取消、单标的回测契约。

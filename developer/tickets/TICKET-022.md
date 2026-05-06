# TICKET-022: 前端回测详情适配器接入真实数据

**优先级:** P1 - 高
**状态:** 📋 待开始
**依赖:** 020, 021
**预计工时:** 0.25d

## 需求描述

前端 API 客户端 [client.ts:281-311](../../frontend/src/api/client.ts#L281-L311) 中的 `taskToResult` 函数将后端返回的 `BackendBacktestResult` 转换为前端 `BacktestResult` 类型，但目前将 `equity_curve`、`drawdown_curve`、`yearly_returns`、`monthly_returns`、`trades` 全部硬编码为 `[]`。TICKET-020/021 完成后，后端将返回这些数据，前端需要接入。

## 根因分析

```typescript
// client.ts:303-307 — 当前实现
equity_curve: [],           // <--- HARDCODED EMPTY
drawdown_curve: [],          // <--- HARDCODED EMPTY
yearly_returns: [],          // <--- HARDCODED EMPTY
monthly_returns: [],         // <--- HARDCODED EMPTY
trades: [],                  // <--- HARDCODED EMPTY
```

## 功能清单

### 1. 更新 BackendBacktestResult 接口
在 [client.ts:264-279](../../frontend/src/api/client.ts#L264-L279) 中添加新字段：

```typescript
interface BackendBacktestResult {
  task_id: string;
  status: string;
  request: { ... } | null;
  metrics: Record<string, number> | null;
  error: string | null;
  created_at: string;
  completed_at: string | null;
  // 新增
  equity_curve: CurvePoint[] | null;
  drawdown_curve: CurvePoint[] | null;
  benchmark_curve: CurvePoint[] | null;
  yearly_returns: YearlyReturn[] | null;
  monthly_returns: MonthlyReturn[] | null;
  trades: Trade[] | null;
}
```

### 2. 更新 taskToResult 映射
将硬编码 `[]` 替换为从 `task` 读取：

```typescript
equity_curve: task.equity_curve || [],
drawdown_curve: task.drawdown_curve || [],
benchmark_curve: task.benchmark_curve || undefined,
yearly_returns: task.yearly_returns || [],
monthly_returns: task.monthly_returns || [],
trades: task.trades || [],
```

### 3. 更新 strategy_id 映射（顺手修复）
当前 `strategy_id: 0` 硬编码。如果后端 request 中有 strategy_id 则读取，否则保持 0 为 fallback。

## 验收标准

- [ ] Mock 模式下回测详情页仍然正常（不受影响）
- [ ] 真实 API 模式下，回测完成后净值曲线图展示正常曲线而非空图
- [ ] 回撤曲线图展示正常
- [ ] 年度收益柱状图和月度热力图展示数据
- [ ] 交易记录表格显示买卖记录
- [ ] pending/running 状态任务不报错（新字段为 null 时 fallback 到 `[]`）

## 备注

- 前端不需要改 UI 组件，只改 adapter 层。UI 组件已经完整实现了空数据处理（显示"暂无数据"），接入真实数据后直接工作。
- 注意 Date 格式：后端返回 `"2024-01-15"` 字符串，前端 `CurvePoint.date` 也是 `string`，无需转换。

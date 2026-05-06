# TICKET-046: 前端 BacktestResult 映射函数去重

**优先级:** P2 - 中
**状态:** ✅ 已完成
**依赖:** TICKET-034, TICKET-036
**预计工时:** 0.5d

## 症状

`frontend/src/api/client.ts` 中存在三套相似的后端回测结果映射函数：

- `historyItemToResult()`
- `taskToResult()`
- `strategyResultToBacktestResult()`

三者都在构造 `BacktestResult.metrics`、曲线数组、交易列表与状态字段，但默认值和字段来源不完全一致。后续新增字段时需要同步修改三处，容易重新出现列表页、详情页、策略详情页展示不一致。

## 根因分析

不同后端端点返回结构不完全一致，但前端没有共享的规范化层。当前代码把“端点差异处理”和“BacktestResult 默认值填充”耦合在每个 mapper 内。

## 修复方案

### 1. 抽取共享构造器

**文件**: `frontend/src/api/client.ts`

新增内部 helper，例如：

- `emptyBacktestMetrics(overrides?)`
- `mapTrades(trades?)`
- `buildBacktestResult(input)`

各端点 mapper 只负责把自身 payload 转换成共享输入结构。

### 2. 保持端点差异可读

- 历史列表缺少详情曲线时仍返回空数组
- 任务详情和策略结果保留 `benchmark_curve`
- `strategy_id` 不再默默丢失或回退错误

### 3. 补充单测

**文件**: `frontend/src/api/__tests__/client.test.ts`

覆盖三类 payload 映射到一致的默认 metrics、status、trades。

## 实施结果

### 新增共享 helper（client.ts 内部）

- `emptyBacktestMetrics()` — 返回全部为 0 的 BacktestMetrics 对象
- `mapTrades(trades?)` — 统一将后端交易数组映射为前端 `Trade[]`
- `buildBacktestResult(input)` — 核心构造器，接收规范化的 `BacktestResultInput`，输出统一的 `BacktestResult`
- `BacktestResultInput` interface — 三个端点 mapper 的共享中间表示

### 改造后各 mapper 职责清晰

- `historyItemToResult` — 仅提取历史列表特有字段，其余由 `buildBacktestResult` 填充
- `taskToResult` — 展开 `request` 子对象，传递完整曲线/交易数据
- `strategyResultToBacktestResult` — 直接透传扁平化结构

### 验收标准

- [x] `client.ts` 中重复的 metrics/trades/default array 构造逻辑收敛到共享 helper
- [x] 三个接口的现有调用行为保持兼容（153 tests passed, build succeeds）
- [x] `cd frontend && npm run test` → 153 tests passed (含 client.test.ts 全部 8 个 backtest 测试)
- [x] `cd frontend && npm run build` → built in 607ms
- [x] `cd frontend && npx eslint src/api/client.ts` → 0 errors
- [x] TypeScript 编译零错误 (`tsc --noEmit`)

## 备注

- 本工单是维护性重构，避免后续回测字段扩展反复遗漏
- 审查时间: 2026-05-06
- 来源: `developer/auto-code-review/report_full_20260506.md` — 2.2 前端分层警惕信号、4.2 前端 TypeScript 断点

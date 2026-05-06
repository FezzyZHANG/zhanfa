# TICKET-021: 后端 API 模型补充时序/交易数据字段

**优先级:** P1 - 高
**状态:** 📋 待开始
**依赖:** 020
**预计工时:** 0.25d

## 需求描述

TICKET-020 完成后，backend service 层已有曲线和交易数据，但 Pydantic 模型 `BacktestResult` 和 `BacktestMetrics`（[models.py:190-209](../../src/zhanfa/api/models.py#L190-L209)）缺少对应字段，导致 API 序列化时数据被丢弃。需要更新模型并同步调整路由序列化逻辑。

## 根因分析

```python
# models.py 当前 BacktestResult:
class BacktestResult(BaseModel):
    task_id: str
    status: str
    request: BacktestRequest | None = None
    metrics: BacktestMetrics | None = None   # 只有 9 个标量
    error: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
    # 缺少: equity_curve, drawdown_curve, benchmark_curve,
    #        yearly_returns, monthly_returns, trades
```

## 功能清单

### 1. 新增 Pydantic 子模型
```python
class CurvePoint(BaseModel):
    date: str
    value: float

class YearlyReturn(BaseModel):
    year: int
    value: float

class MonthlyReturn(BaseModel):
    year: int
    month: int
    value: float

class TradeRecord(BaseModel):
    date: str
    action: str  # buy / sell
    price: float
    quantity: float
    pnl: float | None = None
```

### 2. 更新 BacktestResult 模型
添加新字段（全部可选，兼容 pending/running 状态下的 null）：
```python
class BacktestResult(BaseModel):
    task_id: str
    status: str
    request: BacktestRequest | None = None
    metrics: BacktestMetrics | None = None
    error: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
    # 新增
    equity_curve: list[CurvePoint] | None = None
    drawdown_curve: list[CurvePoint] | None = None
    benchmark_curve: list[CurvePoint] | None = None
    yearly_returns: list[YearlyReturn] | None = None
    monthly_returns: list[MonthlyReturn] | None = None
    trades: list[TradeRecord] | None = None
```

### 3. 更新路由
[backtest.py:28-33](../../src/zhanfa/api/routers/backtest.py#L28-L33) 的 `get_task` 端点已使用 `response_model=BacktestResult`，模型更新后自动生效。确认 service 的 `get_task` 返回 dict 中的新字段能正确映射到模型。

### 4. 更新 BacktestHistoryItem（可选）
列表视图不需全部数据，但可考虑加 `trade_count` 等摘要字段。

## 验收标准

- [ ] FastAPI `/docs` Swagger 中 `GET /api/backtest/{task_id}` 的 Response schema 包含新字段
- [ ] 前端调用真实 API 时，响应 JSON 包含 `equity_curve`, `drawdown_curve`, `trades` 等字段
- [ ] pending/running 状态的任务，这些字段为 null 不报错
- [ ] 反向兼容：前端 mock 模式不受影响

## 备注

- 新字段全部设为 `None` 默认值以避免破坏 pending/running 状态的已有行为
- `CurvePoint` 的 `date` 用字符串格式（`"2024-01-15"`），前端直接消费

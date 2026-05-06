# TICKET-023: 数据库模型补充回测时序数据列

**优先级:** P2 - 中
**状态:** 📋 待开始
**依赖:** 021, 027
**预计工时:** 0.25d

## 需求描述

ORM 模型 `BacktestResult`（[models.py:110-126](../../src/zhanfa/db/models.py#L110-L126)）只有 `metrics` (JSON) 和 `report_md` (Text) 列，缺少存储净值曲线、回撤曲线、交易记录等时序数据的列。当前后端使用内存字典存储任务，但一旦切换为 DB 持久化，这些数据将无处存放。

## 功能清单

### 1. 新增 JSON 列
```python
class BacktestResult(Base):
    # ... existing columns ...
    equity_curve = Column(JSON)        # [{date, value}]
    drawdown_curve = Column(JSON)      # [{date, value}]
    benchmark_curve = Column(JSON, nullable=True)
    yearly_returns = Column(JSON)      # [{year, value}]
    monthly_returns = Column(JSON)     # [{year, month, value}]
    trades = Column(JSON)              # [{date, action, price, quantity, pnl}]
```

### 2. 生成 Alembic 迁移
- 运行 `alembic revision --autogenerate -m "add backtest time-series columns"`
- 确认迁移脚本正确
- 测试 upgrade / downgrade

### 3. 更新 DB CRUD（如已有）
如果 `src/zhanfa/db/` 下有 backtest 相关 CRUD，同步更新 read/write 逻辑以处理新列。

## 验收标准

- [ ] 迁移后 `backtest_results` 表包含新列
- [ ] `alembic upgrade head` 和 `alembic downgrade -1` 无错误
- [ ] 新列允许 NULL（兼容已有行）
- [ ] SQLite 和 PostgreSQL 均兼容（JSON 列在 SQLite 中存为 TEXT）

## 备注

- 每条回测结果的 equity_curve 约有 1200+ 个点，存入 SQLite JSON 列约 50KB，可接受
- 当前服务层仍用内存 dict，TICKET-023 是预备性工作——为后续持久化铺路
- 如后续数据量过大，可考虑将时序数据存为 parquet 文件，只在 DB 中存文件路径

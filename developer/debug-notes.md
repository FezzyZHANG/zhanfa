# Debug Notes

常见问题排查记录。

## 策略入口显示异常

**症状**: 前端策略列表/详情页显示英文标识符而非中文名称，或报错。

**排查**:

1. 检查 `frontend/.env` 中 `VITE_ENABLE_MOCK`：`true` 用 mock 数据，`false` 调后端 API
2. 检查 DB 中的策略注册状态：
   ```bash
   python -c "
   from zhanfa.db.base import SessionLocal
   from zhanfa.db.models import Strategy
   s = SessionLocal()
   for r in s.query(Strategy).order_by(Strategy.id).all():
       print(f'id={r.id} name={r.name} code_ref={r.code_ref is not None}')
   s.close()
   "
   ```
3. `code_ref` 必须是完整模块路径 `package.module.ClassName`（如 `zhanfa.strategies.trend.sma_cross.SMACross`）
4. 删除 `code_ref = NULL` 的孤儿策略

## 策略名更新后 DB 不生效

`register_strategies()` 在 FastAPI lifespan 中通过 `code_ref` 做 upsert，重启后端即可。如果仍不生效：确认 `code_ref` 一致、`name` 在类定义中（非实例属性）、无唯一约束冲突。

## 回测提交失败

**症状**: 返回 500 或 `ValueError: Unknown strategy`。

1. 确认 `strategy` 字段是有效 `code_ref`：`curl -s http://127.0.0.1:8000/api/strategies | python -m json.tool | grep code_ref`
2. 验证解析：`python -c "from zhanfa.api.services.strategy_service import _resolve_code_ref; print(_resolve_code_ref('zhanfa.strategies.momentum.rsi_strategy.RSIStrategy'))"`
3. 如 DB 不可用，检查 `_resolve_code_ref` 的 fallback 字典

## akshare 中文列名在 Windows GBK 终端乱码

**症状**: akshare 返回的 DataFrame 列名为 UTF-8 编码的中文字符，在 Windows GBK (cp936) 终端下 print 显示为乱码（如 `����`）。

**根本原因**: Python 3.x 在 Windows 终端默认使用系统代码页（GBK/cp936），而 akshare 底层（东方财富/新浪 API）返回 UTF-8 数据。当 `PYTHONIOENCODING` 未设置时，`print()` 尝试将 UTF-8 字符串编码为 GBK 输出，中文字符无法映射导致乱码。

**解决方案**:
```python
import os
os.environ["PYTHONIOENCODING"] = "utf-8"
```
放在所有 import 之前。此设置强制 Python 使用 UTF-8 进行标准输出编码。

**注意**:
- 仅在 Windows 中文环境需要；Linux/macOS 默认 UTF-8 不受影响
- `stock_zh_a_hist_min_em` 返回中文列名（时间/开盘/收盘/最高/最低/成交量/成交额/涨跌幅/涨跌额/振幅/换手率），映射表见 [fetcher.py:136-140](src/zhanfa/data/fetcher.py)
- `stock_zh_a_minute` (Sina) 返回英文列名（day/open/high/low/close/volume/amount），无此问题
- Notebook (.ipynb) 环境通常已是 UTF-8，不受影响

## 2026-05-05 全面代码审查 Debug 工单

本次审查将 7 个发现拆分为独立工单：

- `TICKET-031`: 前端生产构建失败。已取消并拆分为 `TICKET-038`、`TICKET-039`、`TICKET-040`。
- `TICKET-032`: API 测试隔离数据库。测试导入生产 app 后写入默认 `data/zhanfa.db`，导致唯一约束冲突和测试污染。
- `TICKET-033`: 修复回测止损/止盈参数语义。`vectorbt` 的 `sl_stop/tp_stop` 应直接传入 0.1/0.3 等比例距离，不能转换为 0.9/1.3。
- `TICKET-034`: 回测结果持久化与策略结果联动。当前 `_tasks` 是进程内存，服务重启丢失历史，策略详情无法看到新回测。
- `TICKET-035`: 数据刷新 `freq` 参数被忽略。分钟级强制刷新会删除分钟缓存，但实际调用日线刷新。
- `TICKET-036`: 策略详情回测记录未按策略过滤。真实 API 模式忽略 `strategyId`，所有历史被映射成 `strategy_id: 0`。
- `TICKET-037`: 行业比较前端接入真实 API。后端接口已存在，前端真实模式仍返回 `undefined`。
- `TICKET-038`: 前端 TypeScript 配置与核心类型修复。
- `TICKET-039`: lightweight-charts v5 API 迁移。
- `TICKET-040`: 前端页面/组件严格类型清理。

验证命令记录：

```bash
uv run pytest -q       # 修复前: 216 passed, 2 failed；修复后: 220 passed
uv run ruff check src tests
uv run mypy src
cd frontend && npm run test   # 129 passed
cd frontend && npm run build  # 修复后通过；仍有 Vite chunk size warning
```

2026-05-05 并行修复记录：

- `TICKET-032`: 使用独立临时 SQLite 文件库运行测试，避免污染 `data/zhanfa.db`；内存 SQLite 在线程池执行回测时会因连接隔离导致 `no such table`。
- `TICKET-033`: `sl_stop` / `tp_stop` 直接按 vectorbt 的比例距离语义传入，例如 `0.1` 表示 10%。
- `TICKET-038` / `TICKET-039` / `TICKET-040`: 取消原 `TICKET-031` 后拆分完成，前端生产构建恢复通过。

## 分钟级数据 (stock_zh_a_minute) 注意事项

**固定 1,970 行限制**: Sina `stock_zh_a_minute` 所有频率均固定返回 1,970 行，无法通过 `start_date` 参数获取更早数据。低频（bar 长）= 覆盖更多日历时间：1h 约 2 年，15min 约 6 个月，1min 约 8 天。

**volume/amount 为字符串**: Sina 返回的成交量/成交额 dtype 为 `str`（东方财富返回 `int64`/`float64`）。使用前必须 `pd.to_numeric()` 转换，否则 `Pipeline.clean()` 中的 `df['volume'] == 0` 判断会失败。

**东方财富 1d 不可用**: `stock_zh_a_hist_min_em(period="1d")` 返回单日盘中数据（240 行），不是日线 OHLC。日线数据请使用 `stock_zh_a_hist(period="daily")`。

**数据滚动**: Sina 的 1,970 行固定窗口会随交易日滚动。首次拉取只能拿到最近窗口，需持续 T+1 更新才能累积更长历史。

## 数据初始化与自选股外键

**症状**: 空数据库环境中，股票搜索能从 akshare 返回结果，但添加到自选股时报外键错误；数据管理页统计长期为 0。

**原因**: `watchlist_items.code` 指向 `stocks.code`，而早期刷新流程只写 parquet 缓存，不会把 `stock_list` 导入 `stocks` 表。

**当前约定**:

- `POST /api/data/initialize` 拉取并缓存全 A 股列表，然后导入 `stocks`。
- `POST /api/data/refresh` 在 `discover_new=true` 时同步导入股票元信息，再拉取日线。
- `add_item()` / `batch_add_items()` 会在写入自选股前确保缺失的 `Stock` 记录存在，避免 FK 错误。

## 前端构建 & API 测试

```bash
cd frontend && npx tsc --noEmit   # 类型检查
cd frontend && npx vite build     # 生产构建

# 常用 API
curl http://127.0.0.1:8000/api/strategies      # 策略列表
curl http://127.0.0.1:8000/api/strategies/1     # 策略详情
curl http://127.0.0.1:8000/api/health           # 健康检查
```

# TICKET-029: 分钟级数据批量回填脚本

**优先级:** P2 - 中
**状态:** ✅ 已完成
**依赖:** TICKET-027 (已完成), [Fetcher.minute()](src/zhanfa/data/fetcher.py)
**预计工时:** 0.5d

## 需求描述

创建 `scripts/fetch_minute.py`，批量拉取全市场分钟级数据并缓存到 parquet。支持 1h/15min/30min 三种频率。由于 Sina 固定返回 1,970 行，首次拉取只能获取当前窗口，需持续 T+1 增量运行以积累更长历史。

## 任务清单

### 1. 批量回填脚本

**文件**: `scripts/fetch_minute.py`

```python
"""
全市场分钟级数据批量拉取脚本
用法:
  python scripts/fetch_minute.py --freq 60min   # 1h 数据
  python scripts/fetch_minute.py --freq 15min   # 15min 数据
  python scripts/fetch_minute.py --freq 30min   # 30min 数据
  python scripts/fetch_minute.py --all          # 全部频率
"""
```

功能：
- 自动获取全 A 股列表（通过 `Fetcher.stock_list()` 或 `Store.codes("daily")`）
- 分批拉取（默认每批 100 只），批间休息 2-3 秒
- 进度条显示（tqdm 或手动 print）
- 错误处理：单股票失败不影响其他，记录到 `scripts/fetch_minute_errors.log`
- 支持断点续传：已缓存且今天更新过的跳过（`--force` 强制全量覆写）
- 支持 `--codes 000001,600519` 指定股票

### 2. 调度集成

**文件**: `src/zhanfa/scheduler.py` (或现有调度模块)

在现有 T+1 调度中增加分钟级更新步骤：每日 15:30 后自动触发 `fetch_minute.py --freq 60min`。

或者简单地：`scripts/fetch_minute.py` 支持 `--cron` 模式，被外部 cron/task scheduler 调用。

### 3. 存储预估与验证

脚本运行后输出统计：
```
频率: 60min
更新: 4523 只成功, 12 只失败, 50 只跳过
存储: 661 MB
耗时: 42 分钟
日期范围: 2024-04-18 ~ 2026-04-30
失败详情: scripts/fetch_minute_errors.log
```

## 验收标准

- [x] `python scripts/fetch_minute.py --freq 60min --max 50` 成功拉取 50 只 1h 数据
- [x] 数据可通过 `Fetcher().minute("000001", period="60")` 读取
- [x] 错误日志记录到文件
- [x] `--force` 强制覆写正常
- [x] 帮助信息清晰 (`--help`)

## 备注

- 首次全市场拉取预计 2-3 小时（串行），建议先小批量验证再全量
- 后续 T+1 更新每次仅需 ~40 分钟（全量覆写 1,970 行/股票）
- 如未来 Sina 变更数据接口，脚本编码新调用方即可

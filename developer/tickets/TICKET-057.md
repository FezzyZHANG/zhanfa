# TICKET-057: 补齐发布清单与环境变量文档

**优先级:** P4 - 低
**状态:** ✅ 已完成
**依赖:** -
**预计工时:** 0.5d

## 症状

文档体系已有 `docs/` 与 `developer/` 双轨，但仍缺少两个运维/交付入口：

- `developer/release-checklist.md`: 发布前检查清单
- `developer/environment.md`: 环境变量清单

当前环境变量散落在 `.env`、`config.py`、`fetcher.py`、`api/__init__.py`、Docker Compose 与 CI 中。

## 根因分析

项目从功能开发阶段进入可运行平台阶段后，交付检查与环境配置变成独立知识面。如果只存在于代码中，部署或排障时需要反复 grep/阅读实现。

## 修复方案

### 1. 新增 `developer/environment.md`

覆盖：

- `DATABASE_URL`
- `DATA_DIR`
- `CORS_ORIGINS`
- 缓存 TTL 环境变量
- 调度时间环境变量（与 `TICKET-052` 对齐）
- 前端 `VITE_ENABLE_MOCK`

### 2. 新增 `developer/release-checklist.md`

覆盖：

- 后端 lint/type/test
- 前端 lint/test/build
- 数据库迁移检查
- Docker Compose 启动检查
- 手动 smoke test
- 文档和工单状态检查

### 3. README 索引

在 `developer/README.md` 开发流程区域加入两个文档入口。

## 验收标准

- [ ] `developer/environment.md` 存在并覆盖主要环境变量
- [ ] `developer/release-checklist.md` 存在并可作为发版前核对表
- [ ] `developer/README.md` 能跳转到两份文档
- [ ] 未完成/占位的配置项显式说明并关联工单

## 来源

- `developer/auto-code-review/report_full_20260506.md` — 7 文档体系、P4 路线图第 14 项

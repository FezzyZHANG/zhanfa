# zhanfa (战法) — 项目文档结构

## 文档位置

| 目录 | 用途 |
|------|------|
| `docs/` | 用户/使用文档 — 面向使用者 |
| `developer/` | 开发者文档 — 面向贡献者，含工单跟踪 |

## docs/ — 使用文档

| 文件 | 内容 |
|------|------|
| [index.md](docs/index.md) | 项目入口：技术栈、快速开始、目录概览 |
| [architecture.md](docs/architecture.md) | 分层架构图、各模块职责、API 端点、设计决策 |
| [data.md](docs/data.md) | akshare 封装、缓存管线、关系数据库（ORM 模型/迁移/导入） |
| [strategy.md](docs/strategy.md) | 策略基类接口、指标库、如何添加策略、自动注册 |
| [backtest.md](docs/backtest.md) | vectorbt 回测、绩效指标、JoinQuant 验证、API 回测端点 |

## developer/ — 开发者文档

| 文件 | 内容 |
|------|------|
| [README.md](developer/README.md) | 工单总览 — 工单的状态与依赖关系（你拥有ticket这个skill） |
| [architecture.md](developer/architecture.md) | 系统架构（前端/后端/数据层）、技术选型理由、数据模型 |
| `tickets/TICKET-*.md` | 各工单需求描述与任务清单 |

## 关键约定

- 完成工单后同步更新 `docs/` 和 `developer/` 下的相关文档
- `docs/` 描述"是什么"，`developer/` 描述"为什么"和"怎么做"
- 显式说明未完成或使用占位符的接口或内容，并生成新工单
- 使用`developer/debug-notes.md`读取和写入此项目较为特殊的技术卡点
- When building React components, always include jsdom-compatible test setup with mocks for browser-only APIs (canvas, ResizeObserver, etc.) before writing tests.
- When implementing data pipeline or backend features, always create end-to-end/page-level tests that exercise the full stack (not just unit tests). Verify field names match between frontend display keys and backend response shapes.
- 修复 GitHub CI workflow fail 时，必须先读取 `.github/workflows/ci.yml`，再在本地按失败 job 的同一命令顺序复现和验证；前端 CI 修复必须包含 `npm run lint`，后端 CI 修复必须包含 `uv run ruff check src/`、`uv run mypy src/` 和 `uv run pytest -v`
- 使用 git 管理工单：每个开发型 ticket 使用独立分支，分支名、提交信息、PR 标题必须包含 `TICKET-xxx`；开工、交付和取消时同步更新 `developer/README.md` 与对应 `developer/tickets/TICKET-*.md`

# 开发者工单系统

zhanfa (战法) 前端与后端扩展 —— 需求分析与任务跟踪。

## 当前项目状态

| 维度   | 现状                                       |
| ------ | ------------------------------------------ |
| 语言   | Python 3.11+, uv 管理依赖                  |
| 数据   | akshare → parquet 本地缓存（日线 + 分钟级） |
| 策略   | BaseStrategy 抽象 + SMACross / Turtle 实现 |
| 回测   | vectorbt 引擎 + 自定义指标                 |
| 调度   | schedule 轻量定时任务                      |
| UI     | **React 18 + TypeScript + Vite**           |
| API    | **FastAPI** — RESTful 接口，`/docs` Swagger |
| 数据库 | SQLite (开发) / PostgreSQL (生产)，SQLAlchemy + Alembic |

## 开发流程

- [标准测试流程](testing.md): 工单开发时如何选择定向测试、全量回归、前端构建和手动验证。
- [工程中台角色草稿](platform-ops-role.md): 环境分析、质量控制、工单管理与交付协调的职责边界。
- `auto-code-review/report_full_20260506.md`: 2026-05-06 工程中台全量代码审查报告。

### Git 管理工单

- 每个开发型 ticket 使用独立 git 分支承载，推荐命名为 `ticket/TICKET-xxx-short-title`；自动化或代理创建的分支可保留工具前缀，但必须包含 `TICKET-xxx`。
- 开始工单前，把 `developer/README.md` 与对应 `developer/tickets/TICKET-*.md` 状态更新为 `🔨 进行中`，并在同一分支提交。
- 提交信息与 PR 标题必须包含 ticket 编号，例如 `TICKET-043: 增加降级路径日志`，便于从 git 历史反查需求、验收和验证记录。
- 一个分支原则上只处理一个 ticket；若实现过程中发现新问题，先新增或引用新 ticket，不把无关修复混入当前分支。
- 完成或取消工单时，在对应 ticket 中记录验证结果、残余风险和文档同步情况，并把 `developer/README.md` 状态更新为 `✅ 已完成` 或 `❌ 取消` 后随代码一起提交。

## 工单列表

| 编号   | 标题                   | 优先级      | 状态        | 依赖     |
| ------ | ---------------------- | ----------- | ----------- | -------- |
| [001]  | 前端技术选型与架构设计 | P0 - 紧急   | ✅ 已完成   | -        |
| [002]  | 后端 API 服务设计      | P0 - 紧急   | ✅ 已完成   | -        |
| [003]  | 数据库设计与迁移方案   | P0 - 紧急   | ✅ 已完成   | -        |
| [004]  | K 线图表组件           | P1 - 高     | ✅ 已完成   | 001, 003 |
| [005]  | 财报分析模块           | P1 - 高     | ✅ 已完成   | 001, 003 |
| [006]  | 流派/策略浏览与管理   | P1 - 高     | ✅ 已完成   | 001, 003 |
| [007]  | 自选股票数据库与看板   | P1 - 高     | ✅ 已完成   | 001, 003 |
| [008]  | 回测结果可视化         | P2 - 中     | ✅ 已完成   | 002, 004 |
| [009]  | 部署与 CI/CD           | P2 - 中     | ✅ 已完成   | 001, 002 |
| [010]  | 实现缺失的策略类型     | P2 - 中     | ✅ 已完成   | -        |
| [011]  | 前端 Mock 切换真实 API | P0 - 紧急   | ✅ 已完成   | 010, 012 |
| [012]  | 补充缺失的后端 API     | P1 - 高     | ✅ 已完成   | 003      |
| [013]  | 完善测试覆盖           | P1 - 高     | ✅ 已完成   | 003, 010, 012 |
| [014]  | 增强回测与自动化流程   | P2 - 中     | ✅ 已完成   | 003      |
| [015]  | JQ Adapter 与杂项修复  | P3 - 低     | ✅ 已完成   | -        |
| [016]  | 去重 ORM 模型定义      | P1 - 高     | ✅ 已完成   | 003      |
| [017]  | 补充前端文档           | P2 - 中     | ✅ 已完成   | 001, 004, 005, 006, 007, 008 |
| [018]  | 补充自动化模块文档     | P3 - 低     | ✅ 已完成   | 014      |
| [019]  | 添加前端测试           | P2 - 中     | ✅ 已完成   | 011      |
| [020]  | 后端回测服务补充时序数据提取 | P1 - 高 | ✅ 已完成 | -        |
| [021]  | 后端 API 模型补充时序/交易数据字段 | P1 - 高 | ✅ 已完成 | 020      |
| [022]  | 前端回测详情适配器接入真实数据 | P1 - 高 | ✅ 已完成 | 020, 021 |
| [023]  | 数据库模型补充回测时序数据列 | P2 - 中 | ✅ 已完成 | 021      |
| [024]  | 数据管理后端 — 统计与刷新 API | P1 - 高 | ✅ 已完成 | -        |
| [025]  | 数据管理前端页面 | P1 - 高 | ✅ 已完成 | 024      |
| [026]  | 增强自选股管理 | P2 - 中 | ✅ 已完成 | 024      |
| [027]  | 全A股15分钟数据存储可行性研究 | P2 - 中 | ✅ 已完成 | -        |
| [028]  | 前端图表 + API 支持分钟级数据 | P1 - 高 | ✅ 已完成 | 027      |
| [029]  | 分钟级数据批量回填脚本 | P2 - 中 | ✅ 已完成 | 027      |
| [030]  | 数据初始化缺失导致自选添加与数据管理不可用 | P0 - 紧急 | ✅ 已完成 | - |
| [031]  | 前端生产构建失败 | P1 - 高 | ❌ 取消 | 028, 022 |
| [032]  | API 测试隔离数据库 | P1 - 高 | ✅ 已完成 | 003 |
| [033]  | 修复回测止损/止盈参数语义 | P1 - 高 | ✅ 已完成 | 014 |
| [034]  | 回测结果持久化与策略结果联动 | P2 - 中 | ✅ 已完成 | 020, 021, 023 |
| [035]  | 数据刷新 freq 参数被忽略 | P2 - 中 | ✅ 已完成 | 028, 029 |
| [036]  | 策略详情回测记录未按策略过滤 | P2 - 中 | ✅ 已完成 | 034 |
| [037]  | 行业比较前端接入真实 API | P2 - 中 | ✅ 已完成 | 012 |
| [038]  | 前端 TypeScript 配置与核心类型修复 | P1 - 高 | ✅ 已完成 | 031 |
| [039]  | lightweight-charts v5 API 迁移 | P1 - 高 | ✅ 已完成 | 028, 031 |
| [040]  | 前端页面/组件严格类型清理 | P1 - 高 | ✅ 已完成 | 031 |
| [041]  | 数据缓存可知情与定期更新 | P1 - 高 | ✅ 已完成 | - |
| [042]  | CI pytest 失败 — max_age 测试与编码问题 | P1 - 高 | ✅ 已完成 | 041 |
| [043]  | API 降级路径静默吞错缺少可观测性 | P1 - 高 | ✅ 已完成 | - |
| [044]  | 移除 FastAPI 模块导入阶段的 init_db 副作用 | P1 - 高 | ✅ 已完成 | 032 |
| [045]  | Pydantic 模型可变默认值统一改为 default_factory | P1 - 高 | ✅ 已完成 | - |
| [046]  | 前端 BacktestResult 映射函数去重 | P2 - 中 | 📋 待开始 | 034, 036 |
| [047]  | StockInfo 前后端契约对齐 | P2 - 中 | 📋 待开始 | - |
| [048]  | get_watchlist_quotes 批量行情查询性能优化 | P3 - 低 | 📋 待开始 | 043 |
| [049]  | 行业比较接口逐股抓取财务数据导致响应慢 | P3 - 低 | 📋 待开始 | - |
| [050]  | 回测结果持久化失败缺少日志与失败语义 | P2 - 中 | ✅ 已完成 | 034 |
| [051]  | 回测请求日期格式统一由后端校验转换 | P2 - 中 | 📋 待开始 | - |
| [052]  | 调度时间配置与实际注册值对齐 | P2 - 中 | 📋 待开始 | 041 |
| [053]  | 策略 code_ref fallback 与注册源统一 | P3 - 低 | 📋 待开始 | - |
| [054]  | 补齐关键链路与降级场景测试 | P2 - 中 | ✅ 已完成 | 041, 043 |
| [055]  | Docker 前端等待后端健康后再暴露服务 | P3 - 低 | 📋 待开始 | - |
| [056]  | pre-commit 补齐本地类型与前端质量门禁 | P4 - 低 | 📋 待开始 | - |
| [057]  | 补齐发布清单与环境变量文档 | P4 - 低 | 📋 待开始 | - |
| [058]  | 修复 CI lint 错误（后端 ruff + 前端 ESLint） | P1 - 高 | 📋 待开始 | - |
| [042a] | 恢复 max_age TTL 缓存命中测试 | P2 - 中 | 📋 待开始 | 041 |

## 状态说明

- 📋 待开始 — 尚未开工
- 🔨 进行中 — 正在开发
- ✅ 已完成 — 已交付
- ⛔ 阻塞 — 等待外部依赖
- ❌ 取消 — 不再需要

[001]: tickets/TICKET-001.md
[002]: tickets/TICKET-002.md
[003]: tickets/TICKET-003.md
[004]: tickets/TICKET-004.md
[005]: tickets/TICKET-005.md
[006]: tickets/TICKET-006.md
[007]: tickets/TICKET-007.md
[008]: tickets/TICKET-008.md
[009]: tickets/TICKET-009.md
[010]: tickets/TICKET-010.md
[011]: tickets/TICKET-011.md
[012]: tickets/TICKET-012.md
[013]: tickets/TICKET-013.md
[014]: tickets/TICKET-014.md
[015]: tickets/TICKET-015.md
[016]: tickets/TICKET-016.md
[017]: tickets/TICKET-017.md
[018]: tickets/TICKET-018.md
[019]: tickets/TICKET-019.md
[020]: tickets/TICKET-020.md
[021]: tickets/TICKET-021.md
[022]: tickets/TICKET-022.md
[023]: tickets/TICKET-023.md
[024]: tickets/TICKET-024.md
[025]: tickets/TICKET-025.md
[026]: tickets/TICKET-026.md
[027]: tickets/TICKET-027.md
[028]: tickets/TICKET-028.md
[029]: tickets/TICKET-029.md
[030]: tickets/TICKET-030.md
[031]: tickets/TICKET-031.md
[032]: tickets/TICKET-032.md
[033]: tickets/TICKET-033.md
[034]: tickets/TICKET-034.md
[035]: tickets/TICKET-035.md
[036]: tickets/TICKET-036.md
[037]: tickets/TICKET-037.md
[038]: tickets/TICKET-038.md
[039]: tickets/TICKET-039.md
[040]: tickets/TICKET-040.md
[041]: tickets/TICKET-041.md
[042]: tickets/TICKET-042.md
[043]: tickets/TICKET-043.md
[044]: tickets/TICKET-044.md
[045]: tickets/TICKET-045.md
[046]: tickets/TICKET-046.md
[047]: tickets/TICKET-047.md
[048]: tickets/TICKET-048.md
[049]: tickets/TICKET-049.md
[050]: tickets/TICKET-050.md
[051]: tickets/TICKET-051.md
[052]: tickets/TICKET-052.md
[053]: tickets/TICKET-053.md
[054]: tickets/TICKET-054.md
[055]: tickets/TICKET-055.md
[056]: tickets/TICKET-056.md
[057]: tickets/TICKET-057.md
[058]: tickets/TICKET-058.md
[042a]: tickets/TICKET-042a.md

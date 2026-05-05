# zhanfa 开发文档

自动化投资交易辅助系统 —— A 股策略的**数据获取 → 回测 → JoinQuant 验证**全流程。

## 技术栈

| 层 | 工具 | 用途 |
|---|---|---|
| 环境 | uv + Python 3.11 | 包管理与虚拟环境 |
| 数据 | akshare + pandas + pyarrow | A 股行情/财报获取与缓存 |
| 回测 | vectorbt 0.28 | 向量化回测引擎 |
| API | FastAPI + Pydantic v2 | RESTful 接口服务 |
| 验证 | JoinQuant (聚宽) | 云端仿真/实盘 |

## 环境准备

```bash
git clone <repo>
cd zhanfa
uv sync                       # 安装所有依赖
```

项目根目录的 `.env` 设置了 `PYTHONIOENCODING=utf-8`，避免 Windows 控制台中文乱码。`uv run` 会自动加载。

## 快速开始

```bash
# 启动 API 服务（Swagger UI 在 http://127.0.0.1:8000/docs）
uv run uvicorn zhanfa.api:app --reload

# 启动前端开发服务器（http://localhost:5173）
cd frontend && npm run dev

# 拉取沪深300成分股数据（首次下载，之后读缓存）
uv run python scripts/fetch_data.py

# 运行双均线策略回测
uv run python scripts/run_backtest.py

# 多策略对比 + 可视化
uv run jupyter lab notebooks/01_quickstart.ipynb

# 导出策略到 JoinQuant
uv run python scripts/export_jq.py sma_cross

# 运行测试
uv run pytest tests/ -v
```

## 部署

```bash
# Docker Compose 一键部署
docker compose up -d

# 或轻量部署（无需 Docker）
uv run uvicorn zhanfa.api:app --host 0.0.0.0 --port 8000
cd frontend && npm run build
```

## 目录概览

```
src/zhanfa/
├── api/          FastAPI REST 服务（路由/模型/数据库/服务层）
├── db/           ORM 模型（SQLAlchemy）/ 数据导入 / 策略注册
├── data/         数据获取（akshare）、清洗、本地缓存
├── strategies/   交易策略（趋势/动量/基本面/多因子）
├── backtest/     vectorbt 回测引擎封装
├── jq/           JoinQuant 代码生成
└── automation/   定时调度与工作流

scripts/          可执行入口脚本
notebooks/        Jupyter 研究笔记本
docs/             开发文档
tests/            测试套件（61 个用例）
```

## 文档导航

| 文档 | 内容 |
|---|---|
| [architecture.md](architecture.md) | 分层架构、模块关系、API 设计、关键设计决策 |
| [data.md](data.md) | akshare 封装、数据清洗管线、缓存机制、财务数据处理 |
| [strategy.md](strategy.md) | 策略基类接口、技术指标库、如何添加新策略 |
| [backtest.md](backtest.md) | vectorbt 回测、绩效指标、JoinQuant 验证流程、API 回测端点 |
| [automation.md](automation.md) | 定时调度器、工作流、如何添加作业、当前限制 |
| [frontend.md](frontend.md) | 前端架构、技术栈、路由、组件、Mock 模式、开发流程 |

> **注意**: 本文档描述目标架构。29 个工单已全部完成，核心功能均已交付。如有新的需求或问题，请查阅 `developer/` 下的工单跟踪。

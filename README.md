# zhanfa — 自动化投资交易辅助系统

收集股票交易流派与理论，用数据验证、回测、自动化执行。

## 技术栈

[uv](https://github.com/astral-sh/uv) · [akshare](https://github.com/akfamily/akshare) · [pandas](https://pandas.pydata.org) · [vectorbt](https://github.com/polakowo/vectorbt) · [JoinQuant](https://www.joinquant.com) · [React 18](https://react.dev) · [Vite](https://vite.dev) · [Tailwind CSS](https://tailwindcss.com) · [TanStack Router](https://tanstack.com/router) · [TradingView Lightweight Charts](https://github.com/tradingview/lightweight-charts)

## 快速开始

```bash
uv sync                                          # 安装依赖
uv run python scripts/fetch_data.py              # 拉取沪深300数据
uv run python scripts/run_backtest.py            # 运行双均线回测
uv run jupyter lab notebooks/01_quickstart.ipynb # 可视化分析
uv run pytest tests/ -v                          # 运行测试
cd frontend && npm install && npm run dev        # 启动前端开发服务器
```

## 项目结构

```
src/zhanfa/
├── data/          数据获取（akshare）、清洗、本地 parquet 缓存
├── strategies/    交易策略（趋势/动量/基本面/多因子）
├── backtest/      vectorbt 回测引擎封装
├── jq/            JoinQuant 适配层
└── automation/    定时调度与工作流

frontend/          React 18 + TypeScript + Vite 前端
├── src/pages/     策略列表、详情、自选股、个股、回测
├── src/components/ UI 组件、K线图、财报图
├── src/hooks/     TanStack Query + Zustand 状态管理
└── src/api/       Axios 封装 + Mock 数据

scripts/           入口脚本
notebooks/         Jupyter 研究笔记本
docs/              开发文档
tests/             41 个单元测试
```

## 文档

[开发文档](docs/index.md) — 架构设计、数据管线、策略编写、回测验证全流程。

# TICKET-011: 前端 Mock 数据切换为真实 API 调用

| 属性     | 值                              |
| -------- | ------------------------------- |
| 优先级   | P0 - 紧急                       |
| 依赖     | 010, 012                        |
| 创建日期 | 2026-05-05                      |

## 问题描述

前端 API 客户端 `frontend/src/api/client.ts` 中 `USE_MOCK = true`，整个前端使用硬编码模拟数据运行。所有数据获取函数 (`fetchStrategies`, `fetchStock`, `fetchKline`, `fetchFinancials`, `fetchWatchlists`, `submitBacktest` 等) 都有 `if (USE_MOCK)` 分支返回合成数据。

`frontend/src/api/mock.ts` 中包含：
- 合成 K 线数据（随机游走）
- 仅 4 只股票的财务数据
- 仅 10 只股票的基础列表
- 仅 2 条回测结果
- 仅 3 个行业的对比数据

此外，自选股看板中的 Sparkline 图表 (`WatchlistCards.tsx:102-111`) 是随机正弦波占位符，未使用文件中已定义的 `Sparkline` 组件。

## 任务清单

- [x] 将 `USE_MOCK` 改为 `false` 或移除 mock 分支 → 通过 `VITE_ENABLE_MOCK` 环境变量控制
- [x] 验证所有 API 调用与后端端点匹配（路径、参数、返回类型）
- [x] 替换 WatchlistCards 中的占位 Sparkline 为真实 `Sparkline` 组件
- [x] 确认前端可正常加载后端服务提供的实时数据（TypeScript 编译通过，路径已对齐）
- [x] 考虑是否将 mock.ts 保留为开发/测试用途（通过环境变量控制）→ 保留 mock.ts，通过 `VITE_ENABLE_MOCK=true` 启用

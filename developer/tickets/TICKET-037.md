# TICKET-037: 行业比较前端接入真实 API

**优先级:** P2 - 中
**状态:** ✅ 已完成
**依赖:** TICKET-012
**预计工时:** 0.5d

## 症状

后端已经提供行业比较接口：

```text
GET /api/stocks/industry/{industry}/comparison
```

但前端真实 API 模式仍直接返回 `undefined`：

```ts
// No backend endpoint yet (TICKET-012)
return undefined;
```

因此行业雷达图/行业对比组件在 mock 模式可用，切到真实 API 后没有数据。

## 根因分析

TICKET-012 已补充后端 API，但前端 client 仍保留旧占位逻辑，没有同步接入真实端点。

## 修复方案

### 1. 接入真实行业比较接口

**文件**: `frontend/src/api/client.ts`

将真实 API 模式改为：

```ts
const { data } = await api.get<IndustryComparison>(
  `/stocks/industry/${encodeURIComponent(industry)}/comparison`
);
return data;
```

### 2. 补充错误/空状态

**文件**:

- `frontend/src/hooks/useIndustryComparison.ts`
- 使用 `IndustryRadar` 的页面/组件

处理：

- 行业为空时不请求
- 后端返回空 peers 时展示空状态
- 请求失败时展示错误提示或降级状态

### 3. 补充测试

**文件**: `frontend/src/api/__tests__/client.test.ts`

覆盖：

- mock 模式读取 mock 数据
- 真实模式调用 `/stocks/industry/{industry}/comparison`
- 中文行业名正确 URL 编码

## 验收标准

- [x] 真实 API 模式下行业比较能返回 peers 数据
- [x] 中文行业名请求路径正确
- [x] 空行业/空数据/失败状态不会导致页面崩溃
- [x] `cd frontend && npm run test` 通过

## 备注

- 审查时间: 2026-05-05
- 原注释中的 TICKET-012 已完成，应删除旧占位说明

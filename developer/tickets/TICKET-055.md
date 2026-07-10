# TICKET-055: Docker 前端等待后端健康后再暴露服务

**优先级:** P3 - 低
**状态:** ✅ 已完成
**依赖:** -
**预计工时:** 0.5d

## 症状

`docker-compose.yml` 中 `backend` 等待 `db` healthy，但 `frontend` 只声明：

```yaml
depends_on:
  - backend
```

如果后端首次启动较慢，nginx 可能已经对外暴露，但 upstream 暂不可用，用户会短暂看到 502。

## 根因分析

Compose 只保证启动顺序，不保证服务 ready。后端没有 healthcheck，前端也没有用 `condition: service_healthy` 等待后端健康。

## 修复方案

### 1. 为 backend 增加 healthcheck

检查 `/api/health`：

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
```

如镜像内无 curl，可用 Python 标准库或安装轻量工具。

### 2. frontend depends_on 使用 health 条件

```yaml
depends_on:
  backend:
    condition: service_healthy
```

### 3. 本地验证

`docker compose up --build` 首次启动时，前端不应在 backend ready 前暴露不可用 upstream。

## 验收标准

- [ ] backend 有可用 healthcheck
- [ ] frontend 等待 backend healthy
- [ ] 首次启动不出现稳定可复现的 nginx upstream 502
- [ ] `docker compose config` 通过

## 来源

- `developer/auto-code-review/report_full_20260506.md` — 6.2 Docker

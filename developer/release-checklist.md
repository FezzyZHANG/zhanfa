# 发布前检查清单

每次发布前逐项核对，全部通过后再打 tag 或合并到 `master`。

## 代码质量

- [ ] 后端 lint 通过：`uv run ruff check src/`
- [ ] 后端类型检查通过：`uv run mypy src/`
- [ ] 后端测试通过：`uv run pytest -v`
- [ ] 前端 lint 通过：`cd frontend && npm run lint`
- [ ] 前端构建通过：`cd frontend && npm run build`
- [ ] 前端测试通过：`cd frontend && npm test -- --run`

以上命令组合见 `.github/workflows/ci.yml`。建议在本地先跑 CI 相同命令再推送。

## 数据库

- [ ] `alembic upgrade head` 无报错
- [ ] `alembic history` 确认迁移链完整无断裂
- [ ] 若新增迁移，`alembic downgrade -1` 可回滚

## Docker

- [ ] `docker compose config` 无语法错误
- [ ] `docker compose up --build` 启动后后端 `/api/health` 返回 200
- [ ] 前端 nginx 不返回 502（后端健康检查生效后再暴露）
- [ ] `docker compose down -v` 可干净清理

## 手动验证 (smoke test)

- [ ] 前端首页加载正常（无白屏/JS 错误）
- [ ] 策略列表可展示
- [ ] 自选股页面可添加/删除股票
- [ ] K 线图可正常渲染（日线和分钟线均可用）
- [ ] 财报页面数据可加载
- [ ] 回测可正常提交并查看结果
- [ ] 数据管理页面可查看缓存状态

## 文档与工单

- [ ] 本次发布涉及的工单状态已更新为 `✅ 已完成`
- [ ] `developer/README.md` 工单表格状态正确
- [ ] 新增功能已在 `docs/` 下更新对应文档
- [ ] `developer/environment.md` 覆盖本次新增/变更的环境变量
- [ ] 若有未完成的占位接口，已生成新工单

## Git

- [ ] 所有提交信息包含 TICKET 编号
- [ ] PR 标题包含 TICKET 编号
- [ ] 分支已 squash/rebase 到干净的提交历史
- [ ] 确认未引入 `pyproject.toml` / `uv.lock` 中的意外依赖变更

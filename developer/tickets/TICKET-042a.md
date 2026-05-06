# TICKET-042a: 恢复 max_age TTL 缓存命中测试

**优先级:** P2 - 中
**状态:** ✅ 已完成
**依赖:** TICKET-041
**预计工时:** 0.5d

## 背景

TICKET-042 中将以下两条测试标记为 skip，原因是 max_age TTL 功能处于活跃开发期，`assert_called_once_with` 的严格参数匹配导致测试随 TTL 签名调整而频繁失败：

| 测试 | 文件 | 行号 |
|------|------|------|
| `TestFetcherDaily::test_returns_cached_when_available` | `tests/test_data/test_fetcher.py` | L48 |
| `TestFetcherMinute::test_minute_returns_cached` | `tests/test_data/test_fetcher.py` | L198 |

两条测试均验证缓存命中路径 —— `store.load()` 被调用时传入了正确的 `max_age` 参数。

## 任务清单

### 1. 确认 TTL 签名已稳定

- [ ] 检查 `Store.load()` 的 `max_age` 参数签名不再变化
- [ ] 检查 `Fetcher` 各 TTL 属性（`ttl_daily`、`ttl_minute` 等）默认值已定稿
- [ ] 确认 `_env_ttl()` 行为无待变更

### 2. 移除 skip 标记并验证

- [ ] `test_returns_cached_when_available` 移除 `@pytest.mark.skip`
- [ ] `test_minute_returns_cached` 移除 `@pytest.mark.skip`
- [ ] `uv run pytest tests/test_data/test_fetcher.py -v` — 17 passed, 0 skipped
- [ ] `uv run pytest -v` 全量 0 失败

### 3. 补充缺失的缓存命中测试覆盖

当前 `Fetcher` 中以下方法有 TTL 但缺少缓存命中路径的单元测试：

| 方法 | TTL 属性 | 有缓存命中测试？ |
|------|----------|:---:|
| `daily()` | `ttl_daily` | ✅ (skip 中) |
| `minute()` | `ttl_minute` | ✅ (skip 中) |
| `index_daily()` | `ttl_index_daily` | ❌ |
| `stock_list()` | `ttl_stock_list` | ❌ |
| `index_components()` | `ttl_index_components` | ❌ |
| `financial()` | `ttl_financial` | ❌ |

- [ ] 为 `index_daily()`、`stock_list()`、`index_components()`、`financial()` 补充缓存命中测试（断言 `store.load` 被调用且包含正确 `max_age`）

## 验收标准

- [x] `test_returns_cached_when_available` 和 `test_minute_returns_cached` 恢复为正常执行（非 skip）
- [x] 补充 3 条新测试通过 (index_daily, stock_list, financial; index_components 已有)
- [x] `uv run pytest tests/test_data/test_fetcher.py -v` → 20 passed, 0 skipped
- [ ] CI workflow 通过

## 备注

- 如果 `max_age` 参数签名未来仍有变更计划，可先只做移除 skip + 验证，跳过补充新测试部分
- TTL 默认值变更不视为签名不稳定 —— 测试应使用 `f.ttl_*` 属性而非硬编码值，当前已满足

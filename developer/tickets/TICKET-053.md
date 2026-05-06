# TICKET-053: 策略 code_ref fallback 与注册源统一

**优先级:** P3 - 低
**状态:** ✅ 已完成
**依赖:** -
**预计工时:** 0.5d

## 症状

策略注册存在两套来源：

- `src/zhanfa/db/register_strategies.py` 将策略写入 DB
- `src/zhanfa/api/services/strategy_service.py` 的 `_resolve_code_ref()` 维护硬编码 `_fallback`

新增策略时，如果只更新注册逻辑或只更新 fallback，回测解析可能在空 DB、测试 DB 或初始化失败场景中表现不一致。

## 根因分析

fallback 的目的是 DB 未初始化时仍能解析内置策略，但当前 fallback 手工复制了一份策略列表。策略目录已经具备可发现结构，注册逻辑也已经集中，fallback 不应再维护第二份事实来源。

## 修复方案

### 1. 抽取内置策略清单

新增单一 registry，例如：

- `src/zhanfa/strategies/registry.py`

由 `register_strategies()` 和 `_resolve_code_ref()` 共同读取。

### 2. fallback 从 registry/DB 动态生成

`_resolve_code_ref()` 优先 DB，fallback 使用 registry，不再手写 `_fallback` dict。

### 3. 测试新增策略解析

覆盖：

- DB 有策略记录时按 DB 解析
- DB 空时仍能解析内置策略
- registry 新增策略后注册与 fallback 同步生效

## 验收标准

- [ ] `strategy_service.py` 不再维护第二份硬编码策略 fallback
- [ ] 内置策略清单只有一个事实来源
- [ ] 空 DB 场景仍能创建内置策略实例
- [ ] `uv run pytest tests/test_api/test_strategies*.py tests/test_services -q` 通过

## 来源

- `developer/auto-code-review/report_full_20260506.md` — 3.5 策略注册的双轨制

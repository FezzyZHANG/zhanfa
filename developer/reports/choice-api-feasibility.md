# Choice 量化 API 接入可行性报告

> 评估日期：2026-05-13 | 最新 Choice API 版本：V2.6.1.3（2025-12-16）

## 1. 概述

**Choice 数据量化接口** 是东方财富旗下的商业金融数据 API，基于 `EmQuantAPI` 本地 SDK 提供截面数据、时间序列、财务数据、宏观数据、资讯等功能。目前 zhanfa 唯一的数据源是 **akshare**（免费开源），此报告评估以 Choice 替代或补充 akshare 的可行性。

## 2. Choice API 功能矩阵 vs akshare

### 2.1 数据获取能力对比

| 数据维度 | akshare（现状） | Choice API | 差距 |
|----------|----------------|------------|------|
| **日线 OHLCV** | `stock_zh_a_hist`，26 年历史 | `c.csd("CLOSE,OPEN,HIGH,LOW,VOLUME")` | ≈ 持平 |
| **分钟线** | ~2 年（1h），~6 月（15min） | 需购买增值包（+3 万/年才有 1 年历史） | akshare 更优 |
| **财务数据** | `stock_financial_abstract_ths`，同花顺口径 | `c.css("..." "ROE,EPS,DEBTRATIO...")`，Choice 独家口径 | Choice 更全更标准 |
| **估值数据** | 无专用接口 | `c.css("PE,PB,PS,DIVIDENDYIELD...")` | Choice 独占 |
| **指数成分股** | `index_stock_cons_csindex`（中证指数） | `c.ctr("INDEXCOMPOSITION")`，覆盖更广 | Choice 覆盖更全 |
| **全 A 股列表** | `stock_info_a_code_name()` | `c.sector("001004")` 或 `c.ctr("StockInfo")` | ≈ 持平 |
| **行业板块** | `stock_board_industry_cons_em` | `c.cses(板块代码, 指标)` | ≈ 持平 |
| **宏观数据** | 无 | `c.edb()` — GDP/CPI/PMI/M2/利率等 | **Choice 独占** |
| **资讯/公告** | 无 | `c.cfn()` / `c.cnq()` — 公司新闻/公告/研报 | **Choice 独占** |
| **条件选股** | 无，需自研 | `c.cps()` — SQL-like 多条件筛选 | **Choice 独占** |
| **港股/美股** | akshare 有但不稳定 | 稳定支持 | Choice 更可靠 |
| **期货/外汇/期权** | akshare 部分支持 | 完整支持 | Choice 更全 |
| **数据频次** | 按需拉取 | 按请求次数限频（700次/分钟） | — |

### 2.2 关键差异总结

**Choice 的核心优势：**
1. **宏观数据** — GDP、CPI、PMI、货币供应量等，akshare 无此能力，是策略升级的关键数据源
2. **估值截面** — PE/PB/PS/股息率等不用逐股拉行情算，一次 `c.css` 即可，大幅减少请求量
3. **条件选股 `c.cps()`** — 直接服务端筛选，无需遍历全市场再本地计算
4. **数据稳定性** — 商业合同保障 SLA，akshare 依赖免费源随时可能变更接口
5. **港股/美股** — 对于多市场扩展有战略价值

**akshare 的保留价值：**
1. **分钟线历史深度** — 免费提供 1h 线 2 年、15min 线 6 月，Choice 要额外 +3 万/年
2. **零成本** — 对个人开发者、早期验证、CI 测试均无费用负担
3. **接口简洁** — 函数式调用，无需 SDK 安装和登录激活流程

## 3. 集成架构分析

### 3.1 现状数据流

```
akshare API → Fetcher._clean_*() → Store (parquet) → Pipeline → Strategy/Backtest
```

### 3.2 接入 Choice 后的数据流

```
                    ┌─ akshare API ──┐
Choice SDK ──┤                  ├── Fetcher._clean_*() → Store → Pipeline → ...
                    └─ Choice API ───┘
```

### 3.3 具体改动范围

| 模块 | 改动 | 工作量估计 |
|------|------|-----------|
| `src/zhanfa/data/fetcher.py` | 新增 `ChoiceFetcher` 类或给现有 `Fetcher` 加 choice 分支 | 2-3 天 |
| `src/zhanfa/data/store.py` | 无需改动（parquet 缓存层不变） | 0 |
| `src/zhanfa/data/pipeline.py` | 新增宏观数据列、估值指标列的清洗逻辑 | 1 天 |
| `src/zhanfa/api/services/` | 新数据源的 service 暴露 | 1 天 |
| `src/zhanfa/strategies/` | 新增基于宏观/估值数据的策略（如宏观择时） | 按需 |
| `docker-compose.yml` | 安装 EmQuantAPI SDK 依赖 | 0.5 天 |
| `docs/data.md` / `developer/` | 文档更新 | 0.5 天 |
| CI/CD | 本地/CI 环境通过激活工具绑定令牌 | 0.5 天 |

**总工时估计：5-7 天（不含新策略开发）**

### 3.4 SDK 适配细节

Choice 使用**本地 SDK 模式**（非纯 HTTP API），带来几个工程问题：

1. **原生库依赖**：`EmQuantAPI` 包含 `.so/.dll` 原生库，需按架构分发。Windows/macOS/Linux 各自需要不同的 libs 目录。
2. **登录激活**：首次使用需激活工具（GUI 或短信），生成 `userInfo` 令牌文件。令牌绑定设备，最多 10 台。
3. **进程级单例**：`c.start()` / `c.stop()` 是进程级全局操作。多线程环境需注意锁。
4. **Docker 部署**：容器内需安装 gtk+3.0（macOS）或原生库依赖（Linux），无 GUI 时走短信激活。

### 3.5 建议的封装方式

```python
# 方案 A: 独立 ChoiceFetcher（推荐）
class ChoiceFetcher:
    """Choice 数据获取器，登录/登出自动管理"""

    def __init__(self, store: Store | None = None):
        self._started = False

    def _ensure_login(self):
        if not self._started:
            from EmQuantAPI import c
            c.start()
            self._started = True

    def daily(self, code: str, ...) -> pd.DataFrame:
        self._ensure_login()
        # c.csd(...) → _clean_*() → store.save()

# 方案 B: 在现有 Fetcher 中加 choice_xxx 方法
# 好处是复用 _clean_*() 和 store 逻辑
```

**推荐方案 A**，理由：
- akshare 和 Choice 的调用模式差异大（SDK vs 函数式），强行合并会让 Fetcher 臃肿
- 独立的 `ChoiceFetcher` 便于按需实例化（有令牌才用）
- 共享 `Store` 和 `Pipeline` 层，避免重复建设

## 4. 成本分析

### 4.1 基础费用

| 版本 | 年费（约） | 说明 |
|------|-----------|------|
| 标准版 | **2.5 万元** | CSS/CSD 调用 1000 万次/周 |
| 基础版/个人版 | 可能几千元 | 联系客户经理确认，无公开报价 |

### 4.2 与 zhanfa 相关的增值包

| 增值项 | 年费（约） | zhanfa 是否需要 |
|--------|-----------|----------------|
| CSS/CSD 增量（3000 万次/周） | +2.5 万 | 目前不需要 |
| 历史分钟 K 线（1 年） | +3 万 | 不需要（akshare 覆盖） |
| 财务报表增量（1 万次/周） | +1 万 | 按需 |
| 多点登录增量 | +1-3 万 | 不需要 |

**结论：标准版 2.5 万/年即可覆盖核心需求。** 分钟线和增量频次用 akshare 补充，不产生额外费用。

### 4.3 申请流程

1. 访问 https://choice.eastmoney.com/buyingcenter 注册
2. 客户经理联系 → 申请试用 → 获取测试账号
3. 试用满意后签约 → 获取正式账号 → 设备激活

> 支持**免费试用**，建议先申请试用验证集成可行性后再决定是否采购。

## 5. 风险与注意事项

### 5.1 技术风险

| 风险 | 等级 | 缓解措施 |
|------|------|---------|
| SDK 原生库与 Python 版本不兼容 | 中 | 锁定 py3.11，CI 测所有目标平台 |
| Docker 部署复杂化（需原生库 + 激活） | 中 | 提供无 Choice 的轻量模式（仅 akshare） |
| 令牌文件绑定设备，CI/CD 无法共享 | 中 | CI 走短信激活或使用专有令牌设备 |
| Choice 接口升级/改名 | 低 | 封装隔离，变更只影响 ChoiceFetcher |
| 网络防火墙/代理导致 SDK 连接失败 | 低 | 支持 HTTP_PROXY，SDK 内置代理选项 |
| SDK 单例模式与 FastAPI async 兼容性 | 中 | `_ensure_login()` 加线程锁，或使用单线程 executor |

### 5.2 数据风险

| 风险 | 等级 | 缓解措施 |
|------|------|---------|
| Choice 财务数据口径与 akshare 不同 | 中 | 明确标注数据源，策略参数分开配置 |
| 数据延迟（实时行情非 Choice 强项） | 低 | zhanfa 以日线为主，T+1 延迟可接受 |
| 合约到期后数据访问权丧失 | 高 | 坚持 parquet 本地缓存，合约到期后存量数据仍可用 |

### 5.3 业务风险

- **供应商锁定**：Choice 是本地 SDK 模式，切换成本高于纯 HTTP API。但 akshare 始终保留作为 free fallback。
- **许可限制**：需确认个人开发者或小团队是否可购买（目前主要面向机构），试用时确认。

## 6. 策略价值评估

Choice 为 zhanfa 带来的**新增策略能力**：

| 策略类型 | 所需数据 | Choice 提供 | 当前可行性 |
|----------|---------|-------------|-----------|
| **宏观择时**（美林时钟） | GDP/CPI/PMI/利率 | `c.edb()` | ❌ → ✅ |
| **估值轮动** | PE/PB/PS 截面 | `c.css()` | 可算但不准 |
| **财务多因子选股** | ROE/EPS/毛利率等截面 | `c.cps()` 条件选股 | 需自研 |
| **事件驱动**（公告/研报） | 公司公告、研报 | `c.cfn()` | ❌ → ✅ |
| **行业轮动** | 行业板块资金流/估值 | `c.cses()` | 部分可行 |
| **跨市场套利**（AH 股） | A+H 股同步行情 | CSS 双市场 | ❌ → ✅ |

## 7. 建议路径

### 短期（1-2 周）：申请试用 + PoC

1. 申请 Choice 量化接口免费试用
2. 在开发环境安装 SDK，完成登录激活
3. 实现 `ChoiceFetcher.daily()` 和 `ChoiceFetcher.financial()`，与 akshare 结果交叉验证
4. 验证 Docker 环境下 SDK 可用性

### 中期（1 月）：标准版集成

5. 完成 `ChoiceFetcher` 全部方法
6. 新增 `Fetcher` 工厂或配置选择数据源
7. 添加宏观数据 API 端点
8. 完成文档更新

### 长期（按需）：策略扩展

9. 基于宏观数据开发择时策略
10. 基于估值截面开发多因子策略
11. 基于公告/研报开发事件驱动策略

## 8. 结论

**Choice 量化 API 接入可行，建议推进试用评估。** 核心判断：

- **技术上**：本地 SDK 模式比纯 HTTP API 集成稍复杂，但可控。Docker 部署需额外处理。方案 A（独立 `ChoiceFetcher`）架构清晰，改动范围约 5-7 天。
- **成本上**：标准版 ~2.5 万/年，zhanfa 只需标准版即可（分钟线仍用 akshare），增值包非必需。
- **价值上**：宏观数据、估值截面、条件选股是 akshare 无法覆盖的盲区，能支撑策略从纯技术面升级到宏观+基本面。
- **风险上**：保留 akshare 作为 free fallback，Choice 只作为增强数据源，不会出现单点故障。

**推荐先用试用验证集成，再决策是否采购。**

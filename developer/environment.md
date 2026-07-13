# 环境变量清单

zhanfa 项目所有可配置环境变量。大部分有合理默认值，仅生产部署时需要显式设置。

## 后端

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATABASE_URL` | `sqlite:///data/zhanfa.db` | 数据库连接串。本地开发用 SQLite，生产用 PostgreSQL（如 `postgresql://user:pass@host:5432/db`） |
| `DATA_DIR` | `data` | 本地 parquet 缓存根目录，Docker 中通过 volume 挂载 |
| `API_HOST` | — | FastAPI bind host（如 `0.0.0.0`），Docker 中由 Compose 设置 |
| `API_PORT` | — | FastAPI bind port（如 `8000`），Docker 中由 Compose 设置 |
| `CORS_ORIGINS` | `http://localhost:5173` | 允许的跨域来源，多个用逗号分隔。开发用 Vite 端口，生产用 nginx 端口 |

### 调度时间

所有调度时间格式为 `HH:MM`（北京时间），见 `config.py` 与 `TICKET-052`。

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SCHEDULE_DAILY_UPDATE` | `15:30` | 日线数据更新任务时间 |
| `SCHEDULE_MINUTE_UPDATE` | `15:45` | 分钟数据更新任务时间 |
| `SCHEDULE_WEEKLY_REBALANCE` | `16:00` | 周度调仓/重平衡任务时间 |

### 缓存 TTL

所有 TTL 单位为小时，通过 `fetcher.py` 的 `_env_ttl()` 读取。设置为 `0` 表示始终过期。

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `CACHE_TTL_DAILY_HOURS` | `6` | 日线数据缓存有效期 |
| `CACHE_TTL_INDEX_DAILY_HOURS` | `6` | 指数日线缓存有效期 |
| `CACHE_TTL_STOCK_LIST_HOURS` | `24` | 股票列表缓存有效期 |
| `CACHE_TTL_INDEX_COMPONENTS_HOURS` | `24` | 指数成分股缓存有效期 |
| `CACHE_TTL_INDUSTRY_STOCKS_HOURS` | `24` | 行业成分股缓存有效期 |
| `CACHE_TTL_FINANCIAL_HOURS` | `720` | 财务数据缓存有效期（~30 天） |
| `CACHE_TTL_MINUTE_HOURS` | `6` | 分钟数据缓存有效期 |

### 日线 Provider

腾讯直连默认只用于本地非商业研究。商业、公开或生产用途必须先完成授权评估；不能仅凭技术可用性打开风险接受开关。

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ZHANFA_USAGE_MODE` | `research` | `research` 为本地研究；`commercial` / `production` / `public` 启用授权门禁 |
| `ZHANFA_DAILY_PROVIDER` | `tencent` | 日线主源：`tencent` 或 `akshare` |
| `ZHANFA_DAILY_FALLBACK_ENABLED` | `true` | 主源失败后是否尝试另一个 Provider |
| `ZHANFA_TENCENT_RISK_ACCEPTED` | `false` | 非研究模式完成授权评估后才可显式设为 `true` |
| `ZHANFA_TENCENT_USE_PROXY` | `false` | 腾讯直连是否继承系统代理 |
| `ZHANFA_DAILY_CONNECT_TIMEOUT` | `3.05` | 腾讯连接超时秒数 |
| `ZHANFA_DAILY_READ_TIMEOUT` | `10` | 腾讯读取超时秒数 |
| `ZHANFA_DAILY_MAX_RETRIES` | `3` | 429/5xx、超时、断连和非 JSON 的最大重试次数 |
| `ZHANFA_DAILY_BACKOFF_BASE` | `0.5` | 指数退避基数秒数，另加随机抖动 |
| `ZHANFA_DAILY_MAX_QPS` | `3` | 每个后端进程内所有腾讯 Provider 共享的请求启动速率上限；重试计入，`0` 为显式关闭 |
| `ZHANFA_DAILY_CIRCUIT_FAILURES` | `5` | 连续失败达到此值后熔断 |
| `ZHANFA_DAILY_CIRCUIT_RESET_SECONDS` | `60` | 熔断后的半开等待秒数 |
| `ZHANFA_DAILY_MAX_CONCURRENCY` | `4` | 批量刷新与腾讯请求的并发硬上限 |
| `ZHANFA_DAILY_BATCH_SIZE` | `50` | 每个断点批次的证券数 |
| `ZHANFA_DAILY_BATCH_MAX_CODES` | `500` | 单次工作流最多处理的证券数 |
| `ZHANFA_DAILY_INCREMENTAL_OVERLAP_DAYS` | `7` | 从缓存水位向前重叠抓取的自然日数 |
| `ZHANFA_QFQ_FULL_REFRESH_DAYS` | `30` | 前复权同源全量校准周期 |

### akshare 网络代理

默认情况下，`Fetcher` 调用 akshare 时会临时屏蔽进程继承的
`HTTP_PROXY`、`HTTPS_PROXY`、`ALL_PROXY`、`NO_PROXY` 及其小写形式，避免本机
系统代理意外影响东方财富、Sina 等数据源请求。

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ZHANFA_AKSHARE_USE_PROXY` | `false` | 设为 `true` / `1` / `yes` / `on` 时，允许 akshare 调用继承系统代理环境变量 |

## 前端

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `VITE_ENABLE_MOCK` | `false` | 设为 `true` 启用前端 Mock 数据（无需后端）。在 `frontend/.env` 中设置，Vite 构建时注入 |

## Docker Compose 注入

`docker-compose.yml` 向后端容器注入以下环境变量（覆盖默认值）：

- `DATABASE_URL=postgresql://zhanfa:zhanfa@db:5432/zhanfa`
- `API_HOST=0.0.0.0`
- `API_PORT=8000`
- `CORS_ORIGINS=http://localhost`
- `DATA_DIR=/app/data`

## CI

GitHub Actions CI（`.github/workflows/ci.yml`）未注入特殊环境变量，使用默认值运行 lint/type/test。

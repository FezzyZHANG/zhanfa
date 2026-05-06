# TICKET-003: 数据库设计与迁移方案

**优先级:** P0 - 紧急
**状态:** ✅ 已完成
**依赖:** 无
**预计工时:** 设计 1d + 实现 2d

## 需求描述

设计关系数据库来管理策略元数据、自选股、回测结果等结构化数据。K 线行情数据保留在 parquet 文件中（数据量太大，且已有成熟的 store 层）。

## 数据库选型

| 环境     | 选择             | 理由                          |
| -------- | ---------------- | ----------------------------- |
| 开发     | SQLite           | 零配置、文件级部署             |
| 生产     | PostgreSQL 15+   | 性能、JSONB、全文检索         |

通过 SQLAlchemy + Alembic 实现一键切换，开发/生产用不同连接字符串。

## 表结构设计

### strategies (流派/策略)

```sql
CREATE TABLE strategies (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,  -- SQLite
    -- id       UUID DEFAULT gen_random_uuid(),     -- PostgreSQL
    name        VARCHAR(100) NOT NULL UNIQUE,
    category    VARCHAR(20) NOT NULL,  -- trend/momentum/fundamental/composite
    description TEXT,                   -- Markdown 描述
    params      JSONB NOT NULL DEFAULT '{}',  -- 策略参数 (如 {"fast":20, "slow":60})
    code_ref    VARCHAR(100),           -- 对应 Python 类路径 "zhanfa.strategies.trend.SMACross"
    created_at  TIMESTAMP DEFAULT NOW(),
    updated_at  TIMESTAMP DEFAULT NOW()
);
```

### stocks (股票元信息)

```sql
CREATE TABLE stocks (
    code        VARCHAR(10) PRIMARY KEY,  -- "000001"
    name        VARCHAR(50) NOT NULL,     -- "平安银行"
    exchange    VARCHAR(10),              -- "SZ" / "SH"
    industry    VARCHAR(50),              -- 申万一级行业
    market_cap  DECIMAL(16,2),            -- 总市值 (亿元)
    listed_date DATE,
    is_active   BOOLEAN DEFAULT TRUE,
    updated_at  TIMESTAMP DEFAULT NOW()
);
```

### stock_financial (财报 — 缓存热点数据)

```sql
CREATE TABLE stock_financial (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    code            VARCHAR(10) NOT NULL REFERENCES stocks(code),
    report_date     DATE NOT NULL,            -- 报告期 "2025-12-31"
    net_profit      DECIMAL(16,4),            -- 净利润 (亿元)
    revenue         DECIMAL(16,4),            -- 营业收入 (亿元)
    eps             DECIMAL(10,4),            -- 每股收益
    roe             DECIMAL(8,4),             -- ROE (%)
    debt_ratio      DECIMAL(8,4),             -- 资产负债率 (%)
    current_ratio   DECIMAL(8,4),             -- 流动比率
    gross_margin    DECIMAL(8,4),             -- 毛利率 (%)
    net_margin      DECIMAL(8,4),             -- 净利率 (%)
    dividend_yield  DECIMAL(8,4),             -- 股息率 (%)
    pe              DECIMAL(10,4),            -- 市盈率
    pb              DECIMAL(10,4),            -- 市净率
    UNIQUE(code, report_date)
);
```

### watchlists (自选股分组)

```sql
CREATE TABLE watchlists (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    -- user_id  INTEGER REFERENCES users(id),  -- 多用户时启用
    name        VARCHAR(100) NOT NULL,
    created_at  TIMESTAMP DEFAULT NOW()
);
```

### watchlist_items

```sql
CREATE TABLE watchlist_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    watchlist_id    INTEGER NOT NULL REFERENCES watchlists(id) ON DELETE CASCADE,
    code            VARCHAR(10) NOT NULL REFERENCES stocks(code),
    added_at        TIMESTAMP DEFAULT NOW(),
    notes           TEXT,
    UNIQUE(watchlist_id, code)
);
```

### backtest_results

```sql
CREATE TABLE backtest_results (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id     INTEGER REFERENCES strategies(id),
    stock_codes     JSONB NOT NULL,          -- ["000001","600519"]
    params          JSONB NOT NULL,          -- 回测参数快照
    start_date      DATE NOT NULL,
    end_date        DATE NOT NULL,
    metrics         JSONB NOT NULL,          -- {"total_return":0.35,"sharpe":1.2,...}
    report_md       TEXT,                    -- 完整 Markdown 报告
    status          VARCHAR(20) DEFAULT 'pending', -- pending/running/done/failed
    created_at      TIMESTAMP DEFAULT NOW()
);
```

## 迁移与同步策略

```
akshare API ──→ Fetcher ──→ Parquet (K线，不变)
                │
                └────→ stocks 表 (股票元信息)
                └────→ stock_financial 表 (财报缓存，定期刷新)

CLI 策略扫描 ──→ strategies 表 (自动发现 Python 类并注册)
```

## 验收标准

- [ ] Alembic 迁移脚本生成正确
- [ ] SQLite 下所有表创建成功，外键约束生效
- [ ] 从现有 parquet 数据导入股票元信息和财报到数据库的脚本
- [ ] 策略从 Python 模块自动注册到 strategies 表
- [ ] `uv run alembic upgrade head` 一键建表

## 备注

- stock_daily (K 线) 不放入数据库 — 日线数据每条股票 10 年约 2500 行，3000 只股票 = 750 万行。parquet 列存压缩比好，随机访问通过 `Store.load(code)` 延迟极低。
- 财报数据量小（每只每季一条），放数据库方便按 PE/ROE 等条件筛选和排序。

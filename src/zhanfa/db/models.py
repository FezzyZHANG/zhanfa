"""关系数据库 ORM 模型"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from zhanfa.db.base import Base


class Strategy(Base):
    """策略/流派"""

    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    category = Column(String(20), nullable=False)  # trend/momentum/fundamental/composite
    description = Column(Text)
    params = Column(JSON, nullable=False, default=dict)
    code_ref = Column(String(100))  # zhanfa.strategies.trend.SMACross
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    backtests = relationship("BacktestResult", back_populates="strategy", cascade="all, delete-orphan")


class Stock(Base):
    """股票元信息"""

    __tablename__ = "stocks"

    code = Column(String(10), primary_key=True)
    name = Column(String(50), nullable=False)
    exchange = Column(String(10))
    industry = Column(String(50))
    market_cap = Column(Float)  # 总市值（亿元）
    listed_date = Column(Date)
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.now)

    financials = relationship("StockFinancial", back_populates="stock", cascade="all, delete-orphan")
    watchlist_items = relationship("WatchlistItem", back_populates="stock", cascade="all, delete-orphan")


class StockFinancial(Base):
    """财报数据缓存"""

    __tablename__ = "stock_financial"
    __table_args__ = (
        UniqueConstraint("code", "report_date"),
        Index("ix_stock_financial_code", "code"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), ForeignKey("stocks.code"), nullable=False)
    report_date = Column(Date, nullable=False)
    net_profit = Column(Float)  # 净利润（亿元）
    revenue = Column(Float)  # 营业收入（亿元）
    eps = Column(Float)  # 每股收益
    roe = Column(Float)  # ROE (%)
    debt_ratio = Column(Float)  # 资产负债率 (%)
    current_ratio = Column(Float)  # 流动比率
    gross_margin = Column(Float)  # 毛利率 (%)
    net_margin = Column(Float)  # 净利率 (%)
    dividend_yield = Column(Float)  # 股息率 (%)
    pe = Column(Float)  # 市盈率
    pb = Column(Float)  # 市净率

    stock = relationship("Stock", back_populates="financials")


class Watchlist(Base):
    """自选股分组"""

    __tablename__ = "watchlists"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    items = relationship("WatchlistItem", back_populates="watchlist", cascade="all, delete-orphan")


class WatchlistItem(Base):
    """自选股明细"""

    __tablename__ = "watchlist_items"
    __table_args__ = (UniqueConstraint("watchlist_id", "code"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    watchlist_id = Column(Integer, ForeignKey("watchlists.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(10), ForeignKey("stocks.code"), nullable=False)
    added_at = Column(DateTime, default=datetime.now)
    notes = Column(Text)

    watchlist = relationship("Watchlist", back_populates="items")
    stock = relationship("Stock", back_populates="watchlist_items")


class BacktestResult(Base):
    """回测结果"""

    __tablename__ = "backtest_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(32), index=True)  # API-level UUID for lookups across restarts
    strategy_id = Column(Integer, ForeignKey("strategies.id"), index=True)
    stock_codes = Column(JSON, nullable=False)  # ["000001","600519"]
    params = Column(JSON, nullable=False)  # 回测参数快照
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    metrics = Column(JSON, nullable=False)  # {"total_return":0.35,"sharpe":1.2,...}
    equity_curve = Column(JSON)             # [{date, value}]
    drawdown_curve = Column(JSON)           # [{date, value}]
    benchmark_curve = Column(JSON, nullable=True)
    yearly_returns = Column(JSON)           # [{year, value}]
    monthly_returns = Column(JSON)          # [{year, month, value}]
    trades = Column(JSON)                   # [{date, action, price, quantity, pnl}]
    report_md = Column(Text)  # Markdown 报告
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.now, index=True)

    strategy = relationship("Strategy", back_populates="backtests")

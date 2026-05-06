"""SQLAlchemy 引擎与会话工厂"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from zhanfa.config import config


class Base(DeclarativeBase):
    pass


engine = create_engine(config.database_url, echo=False)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """启用 SQLite 外键约束和 WAL 模式"""
    import sqlite3
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


SessionLocal = sessionmaker(bind=engine)


def init_db():
    """初始化数据库：创建所有表（不使用 alembic 时用于快速开发）"""
    Base.metadata.create_all(bind=engine)


def get_session():
    """FastAPI 依赖注入：获取数据库会话"""
    with SessionLocal() as session:
        yield session

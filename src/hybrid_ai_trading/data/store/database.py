"""
Database Module for Hybrid AI Trading System (Quant Pro v5.2 Ã¢â‚¬â€œ Suite-Aligned, Hedge Fund Grade)
-----------------------------------------------------------------------------------------------
Responsibilities:
- Define SQLite database schema (news + price tables)
- Provide SQLAlchemy session management
- Ensure DB initializes cleanly
- Handle duplicates safely
"""

import logging
import os

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker

from hybrid_ai_trading.config.settings import PROJECT_ROOT

# ---------------------------
# Logging Setup
# ---------------------------
logger = logging.getLogger("hybrid_ai_trading.data.store.database")

# ---------------------------
# DB Config
# ---------------------------
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
os.makedirs(DATA_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "hybrid_ai_trading.db")

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base(metadata=MetaData())

# ---------------------------
# Tables
# ---------------------------


class Price(Base):
    """Price OHLCV table with unique timestamp+symbol constraint."""

    __tablename__ = "prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, index=True)
    symbol = Column(String(20), index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)

    __table_args__ = (
        UniqueConstraint("timestamp", "symbol", name="uix_timestamp_symbol"),
    )


class News(Base):
    """News articles table keyed by external article ID (e.g., Benzinga)."""

    __tablename__ = "news"

    id = Column(Integer, primary_key=True, autoincrement=True)
    article_id = Column(String(50), unique=True, index=True)  # e.g. Benzinga ID
    created = Column(DateTime, index=True)
    title = Column(Text)
    url = Column(Text)
    symbols = Column(Text)


# ---------------------------
# Init
# ---------------------------


def init_db() -> None:
    """Initialize the database (create tables if not exist)."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Ã¢Å“â€¦ Database initialized at %s", DB_PATH)
    except Exception as e:  # noqa: BLE001
        logger.error("Ã¢ÂÅ’ Database initialization failed: %s", e)
        raise


if __name__ == "__main__":
    init_db()

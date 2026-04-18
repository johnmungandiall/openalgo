"""Crypto-specific database models."""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.sql import func
from database.symbol import Base, engine


class FundingRate(Base):
    """Funding rate history."""
    __tablename__ = 'funding_rates'

    id = Column(Integer, primary_key=True)
    symbol = Column(String(50), nullable=False, index=True)
    funding_rate = Column(Float, nullable=False)
    funding_time = Column(DateTime, nullable=False)
    mark_price = Column(Float)
    index_price = Column(Float)
    created_at = Column(DateTime, default=func.now())


class Liquidation(Base):
    """Liquidation history."""
    __tablename__ = 'liquidations'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    symbol = Column(String(50), nullable=False)
    side = Column(String(10), nullable=False)
    quantity = Column(Float, nullable=False)
    liquidation_price = Column(Float, nullable=False)
    loss = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False)


class MarginOperation(Base):
    """Margin add/reduce history."""
    __tablename__ = 'margin_operations'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    symbol = Column(String(50), nullable=False)
    operation = Column(String(10), nullable=False)  # 'ADD' or 'REDUCE'
    amount = Column(Float, nullable=False)
    margin_asset = Column(String(10), nullable=False)
    timestamp = Column(DateTime, default=func.now())


class LeverageSetting(Base):
    """User leverage preferences."""
    __tablename__ = 'leverage_settings'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    symbol = Column(String(50), nullable=False)
    leverage = Column(Integer, nullable=False)
    margin_mode = Column(String(10), nullable=False)  # 'ISOLATED' or 'CROSS'
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


def init_crypto_tables():
    """Initialize crypto-specific tables."""
    Base.metadata.create_all(engine)

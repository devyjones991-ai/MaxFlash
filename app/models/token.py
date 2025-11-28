"""
Модели для токенов и пулов ликвидности.
"""
from sqlalchemy import Column, String, Numeric, Integer, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Token(Base):
    """Модель токена."""
    __tablename__ = "tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    address = Column(String(42), unique=True, index=True, nullable=False)
    chain = Column(String(10), nullable=False)  # 'ethereum' или 'bsc'
    symbol = Column(String(20), index=True)
    name = Column(String(200))
    decimals = Column(Integer, default=18)
    
    # Scam detection результаты
    scam_score = Column(Numeric(5, 4), default=0.0)  # 0.0 - 1.0
    scam_class = Column(String(20))  # 'safe', 'low_risk', 'medium_risk', 'high_risk', 'scam'
    scam_reasons = Column(JSON)  # Список причин скама
    
    # Контракт фичи
    is_proxy = Column(Boolean, default=False)
    is_upgradeable = Column(Boolean, default=False)
    has_blacklist = Column(Boolean, default=False)
    has_whitelist = Column(Boolean, default=False)
    has_mint = Column(Boolean, default=False)
    has_pause = Column(Boolean, default=False)
    tax_buy_percent = Column(Numeric(5, 2), default=0.0)
    tax_sell_percent = Column(Numeric(5, 2), default=0.0)
    
    # Honeypot проверка
    is_honeypot = Column(Boolean, default=False)
    honeypot_test_result = Column(JSON)
    
    # Метаданные
    deployer_address = Column(String(42))
    creation_timestamp = Column(DateTime)
    verified = Column(Boolean, default=False)
    
    # Временные метки
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    pools = relationship("TokenPool", back_populates="token", cascade="all, delete-orphan")
    signals = relationship("Signal", back_populates="token")
    
    def __repr__(self):
        return f"<Token {self.symbol} ({self.address[:10]}...)>"


class TokenPool(Base):
    """Модель пула ликвидности."""
    __tablename__ = "token_pools"
    
    id = Column(Integer, primary_key=True, index=True)
    token_id = Column(Integer, ForeignKey("tokens.id"), nullable=False)
    
    # DEX информация
    dex = Column(String(20), nullable=False)  # 'uniswap_v3', 'pancakeswap'
    pool_address = Column(String(42), unique=True, index=True, nullable=False)
    pair_address = Column(String(42))
    
    # Ликвидность
    liquidity_usd = Column(Numeric(20, 2))
    reserve0 = Column(Numeric(30, 18))
    reserve1 = Column(Numeric(30, 18))
    token0_address = Column(String(42))
    token1_address = Column(String(42))
    
    # LP lock информация
    lp_locked = Column(Boolean, default=False)
    lp_lock_percent = Column(Numeric(5, 2), default=0.0)
    lp_lock_until = Column(DateTime)
    
    # Торговая активность
    volume_24h_usd = Column(Numeric(20, 2), default=0.0)
    transactions_24h = Column(Integer, default=0)
    unique_buyers_24h = Column(Integer, default=0)
    unique_sellers_24h = Column(Integer, default=0)
    buy_sell_ratio = Column(Numeric(5, 2))
    
    # Временные метки
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    token = relationship("Token", back_populates="pools")
    
    def __repr__(self):
        return f"<TokenPool {self.dex} {self.pool_address[:10]}...>"


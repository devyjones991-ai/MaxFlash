"""
Модели для пользователей и подписок.
"""

from sqlalchemy import Column, String, Numeric, Integer, Boolean, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database import Base


class UserRole(str, enum.Enum):
    """Роль пользователя."""

    GUEST = "guest"
    FREE = "free"
    PRO = "pro"
    ALPHA = "alpha"


class SubscriptionStatus(str, enum.Enum):
    """Статус подписки."""

    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class PaymentStatus(str, enum.Enum):
    """Статус платежа."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class User(Base):
    """Модель пользователя."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    # Основная информация
    telegram_id = Column(String(50), unique=True, index=True)
    telegram_username = Column(String(100))
    email = Column(String(200), unique=True, index=True)

    # Роль и доступ
    role = Column(SQLEnum(UserRole), default=UserRole.GUEST, index=True)

    # Настройки уведомлений
    notifications_enabled = Column(Boolean, default=True)
    signal_ratings_enabled = Column(Text)  # JSON список разрешённых рейтингов

    # Временные метки
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_active_at = Column(DateTime)

    # Relationships
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.telegram_username or self.email} ({self.role.value})>"


class Subscription(Base):
    """Модель подписки пользователя."""

    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Подписка
    rating = Column(SQLEnum(UserRole), nullable=False)  # pro или alpha
    status = Column(SQLEnum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE, index=True)

    # Период
    started_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    # Временные метки
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    cancelled_at = Column(DateTime)

    # Relationships
    user = relationship("User", back_populates="subscriptions")

    def __repr__(self):
        return f"<Subscription {self.rating.value} {self.status.value}>"


class Payment(Base):
    """Модель платежа."""

    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)

    # Платеж
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10), default="USD")
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING, index=True)

    # Платёжная система
    payment_provider = Column(String(50))  # 'stripe', 'yookassa', 'crypto'
    payment_id = Column(String(200), unique=True, index=True)

    # Метаданные
    user_metadata = Column(Text)  # JSON с дополнительными данными

    # Временные метки
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)

    # Relationships
    user = relationship("User", back_populates="payments")

    def __repr__(self):
        return f"<Payment {self.amount} {self.currency} {self.status.value}>"

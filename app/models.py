from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime, timezone
import uuid

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    
    user_id = Column(String(100), primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    orders = relationship("Order", back_populates="user")
    wallet = relationship("Wallet", back_populates="user", uselist=False)


class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(String(100), ForeignKey('users.user_id'), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10), nullable=False)
    idempotency_key = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="created")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user = relationship("User", back_populates="orders")
    
    __table_args__ = (
        CheckConstraint('amount > 0', name='check_order_amount_positive'),
    )


class Wallet(Base):
    __tablename__ = "wallets"
    
    customer_id = Column(String(100), ForeignKey('users.user_id'), primary_key=True)
    balance = Column(Numeric(10, 2), nullable=False, default=0)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    
    # Relationships
    user = relationship("User", back_populates="wallet")
    
    __table_args__ = (
        CheckConstraint('balance >= 0', name='check_wallet_balance_non_negative'),
    )

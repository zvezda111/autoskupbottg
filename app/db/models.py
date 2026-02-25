import uuid
import enum

from sqlalchemy import Column, Integer, BigInteger, String, DateTime, ForeignKey, func, Enum as SQLEnum, Sequence
from sqlalchemy.dialects.postgresql import UUID, VARCHAR, INTEGER
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .database import Base


class WithdrawStatus(str, enum.Enum):
    PENDING  = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class Withdrawal(Base):
    __tablename__ = "withdrawals"

    id        = Column(BigInteger, primary_key=True, index=True)
    user_id   = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    amount    = Column(Integer, nullable=False)
    status = Column(
        SQLEnum(
            WithdrawStatus,
            name="withdrawstatus",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
            native_enum=True,
        ),
        nullable=False,
        server_default=WithdrawStatus.PENDING.value
    )
    created_at= Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="withdrawals")

class User(Base):
    __tablename__ = 'users'

    id = Column(BigInteger, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String, index=True)
    balance = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    withdrawals = relationship("Withdrawal", back_populates="user")

    
class Session(Base):
    __tablename__ = 'sessions'

    id = Column(Integer, primary_key=True, index=True)
    hash = Column(String, unique=True, index=True, nullable=False)
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now())


class Check(Base):
    __tablename__ = 'checks'

    id = Column(
        Integer,
        Sequence('checks_id_seq', start=100000, increment=1),
        primary_key=True,
        index=True
    )
    user_id = Column(BigInteger, ForeignKey('users.telegram_id'),nullable=False)
    status = Column(String, nullable=False)
    session_id = Column(Integer, nullable=False)
    region = Column(String)
    price = Column(Integer)
    phone = Column(String, nullable=False, index=True)
    checked_at = Column(DateTime(timezone=True), server_default=func.now())
    check_uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)

class Price(Base):
    __tablename__ = 'prices'

    region_code = Column(String, primary_key=True)   #'RU', 'UA'
    emoji       = Column(String, nullable=False)     #'🇷🇺'
    default_rub = Column(Integer, nullable=False)  
    spamblock_rub  = Column(Integer, nullable=False, default=0)
    overrides   = relationship("UserPrice", back_populates="price")


class MinWithdrawal(Base):
    __tablename__ = 'min_withdrawal'
    min_with = Column(Integer, primary_key=True)


class MaxAccs(Base):
    __tablename__ = 'max_accs'
    max_accs = Column(Integer, primary_key=True)


class UserPrice(Base):
    __tablename__ = 'user_prices'

    user_id       = Column(BigInteger, ForeignKey('users.id'), primary_key=True)
    region_code   = Column(String, ForeignKey('prices.region_code'), primary_key=True)
    price_rub     = Column(Integer, nullable=False)  #обычная цена
    spamblock_rub = Column(Integer, nullable=False, default=0)  #цена за сб

    price = relationship("Price", back_populates="overrides")



import hashlib
import datetime
from phonenumbers import geocoder
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import User, Session, Check, Withdrawal, WithdrawStatus

# юсер
async def get_or_create_user(db: AsyncSession, telegram_id: int, username: str) -> User:
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalars().first()
    if not user:
        user = User(telegram_id=telegram_id, username=username)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user

# сессии
async def get_or_create_session(db: AsyncSession, session_bytes: bytes) -> Session:
    sha = hashlib.sha256(session_bytes).hexdigest()
    result = await db.execute(select(Session).where(Session.hash == sha))
    sess = result.scalars().first()
    if not sess:
        sess = Session(hash=sha)
        db.add(sess)
        await db.commit()
        await db.refresh(sess)
    return sess

# чеки
async def create_check(
    db: AsyncSession,
    user_id: int,
    session_id: int,
    status: str,
    region: str = None,
    price: int = None,
    phone: str = None
) -> Check:
    """
    Создать запись проверки с полем phone.
    """
    check = Check(
        user_id=user_id,
        session_id=session_id,
        status=status,
        region=region,
        price=price,
        phone=phone,
        checked_at=datetime.datetime.utcnow()
    )
    db.add(check)
    await db.commit()
    await db.refresh(check)
    return check

# стата

async def get_stats(
    db: AsyncSession,
    user_id: int,
    since: datetime.datetime
) -> tuple[int, dict[str,int]]:
    count = await db.scalar(
        select(func.count(Check.id))
        .where(
            Check.user_id == user_id,
            Check.checked_at >= since,
            Check.status != 'DUPLICATE'
        )
    )

    rows = await db.execute(
        select(
            Check.region,
            func.count(Check.id)
        )
        .where(
            Check.user_id == user_id,
            Check.checked_at >= since,
            Check.status != 'DUPLICATE'
        )
        .group_by(Check.region)
    )

    breakdown: dict[str,int] = {
        (iso_code if iso_code else 'Неизвестно'): cnt
        for iso_code, cnt in rows.all()
    }

    return count, breakdown

async def request_withdrawal(db: AsyncSession, user: User, amount: int) -> Withdrawal:
    w = Withdrawal(
        user_id = user.id,
        amount  = amount,
        status  = WithdrawStatus.PENDING.value
    )
    db.add(w)
    user.balance -= amount
    db.add(user)
    await db.commit()
    await db.refresh(w)
    return w

async def list_pending_withdrawals(db: AsyncSession) -> list[Withdrawal]:
    q = await db.execute(
        select(Withdrawal)
        .options(selectinload(Withdrawal.user))
        .where(Withdrawal.status == WithdrawStatus.PENDING.value)
    )
    return q.scalars().all()

async def change_withdrawal_status(db: AsyncSession, withdrawal_id: int, new_status: WithdrawStatus):
    w = await db.get(Withdrawal, withdrawal_id)
    if not w:
        return None
    w.status = new_status.value
    db.add(w)
    await db.commit()
    return w
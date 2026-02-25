from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Price, UserPrice

async def get_effective_prices(
    db: AsyncSession,
    user_id: int
) -> list[tuple[str, str, int, int]]:
    q = await db.execute(
        select(
            Price.region_code,
            Price.emoji,
            Price.default_rub,
            Price.spamblock_rub
        )
    )
    price_map: dict[str, dict] = {
        code: {"emoji": emoji, "normal": default, "spam": spam}
        for code, emoji, default, spam in q.all()
    }

    q2 = await db.execute(
        select(
            UserPrice.region_code,
            UserPrice.price_rub.label("user_normal"),
            UserPrice.spamblock_rub.label("user_spam")
        ).where(UserPrice.user_id == user_id)
    )
    for code, user_normal, user_spam in q2.all():
        if code in price_map:
            price_map[code]["normal"] = user_normal
            price_map[code]["spam"]   = user_spam

    return [
        (info["emoji"], code, info["normal"], info["spam"])
        for code, info in price_map.items()
    ]

async def set_default_price(
    db: AsyncSession,
    region_code: str,
    emoji: str,
    default_rub: int,
    spamblock_rub: int = 0
):
    price = await db.get(Price, region_code)
    if price:
        price.emoji        = emoji
        price.default_rub  = default_rub
        price.spamblock_rub= spamblock_rub
    else:
        price = Price(
            region_code   = region_code,
            emoji         = emoji,
            default_rub   = default_rub,
            spamblock_rub = spamblock_rub
        )
        db.add(price)
    await db.commit()


async def set_user_price(
    db: AsyncSession,
    user_id: int,
    region_code: str,
    price_rub: int,
    spamblock_rub: int = 0
):
    up = await db.get(UserPrice, {'user_id': user_id, 'region_code': region_code})
    if up:
        up.price_rub     = price_rub
        up.spamblock_rub = spamblock_rub
    else:
        up = UserPrice(
            user_id       = user_id,
            region_code   = region_code,
            price_rub     = price_rub,
            spamblock_rub = spamblock_rub
        )
        db.add(up)
    await db.commit()

async def delete_region(
    db: AsyncSession,
    region_code: str
) -> None:
    """Удалить регион и все пользовательские переопределения для него."""
    await db.execute(
        delete(UserPrice).where(UserPrice.region_code == region_code)
    )
    await db.execute(
        delete(Price).where(Price.region_code == region_code)
    )
    await db.commit()

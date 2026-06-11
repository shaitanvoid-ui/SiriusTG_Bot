from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import utcnow
from db.models import User
from db.repositories.base import BaseRepo


class UserRepo(BaseRepo):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_tg_id(self, tg_id: int) -> User | None:
        res = await self.session.execute(select(User).where(User.tg_id == tg_id))
        return res.scalar_one_or_none()

    async def upsert_from_tg(
        self,
        *,
        tg_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
        language_code: str | None,
        is_premium: bool,
        referrer_tg_id: int | None = None,
    ) -> tuple[User, bool]:
        user = await self.get_by_tg_id(tg_id)
        created = False
        if user is None:
            user = User(
                tg_id=tg_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                language_code=language_code,
                is_premium=is_premium,
                referrer_tg_id=referrer_tg_id,
                last_seen_at=utcnow(),
            )
            self.session.add(user)
            await self.session.flush()
            created = True
        else:
            user.username = username
            user.first_name = first_name
            user.last_name = last_name
            user.language_code = language_code
            user.is_premium = is_premium
            user.last_seen_at = utcnow()
        return user, created

    async def mark_terms_accepted(self, tg_id: int) -> None:
        await self.session.execute(
            update(User).where(User.tg_id == tg_id).values(accepted_terms_at=utcnow())
        )

    async def mark_captcha_passed(self, tg_id: int) -> None:
        await self.session.execute(
            update(User).where(User.tg_id == tg_id).values(captcha_passed_at=utcnow())
        )

    async def mark_subs_passed(self, tg_id: int, at: datetime | None = None) -> None:
        await self.session.execute(
            update(User).where(User.tg_id == tg_id).values(subs_passed_at=at or utcnow())
        )

    async def clear_subs_passed(self, tg_id: int) -> None:
        await self.session.execute(
            update(User).where(User.tg_id == tg_id).values(subs_passed_at=None)
        )

    async def get_by_id(self, user_id: int) -> User | None:
        res = await self.session.execute(select(User).where(User.id == user_id))
        return res.scalar_one_or_none()

    async def set_referrer(self, tg_id: int, referrer_tg_id: int) -> None:
        await self.session.execute(
            update(User).where(User.tg_id == tg_id).values(referrer_tg_id=referrer_tg_id)
        )

    async def add_balance(self, user_id: int, delta: float) -> None:
        """Прибавляет к балансу. Долг гасится автоматически: если есть debt — сперва списываем в него."""
        user = await self.get_by_id(user_id)
        if user is None:
            return
        if delta <= 0:
            user.balance = round(user.balance + delta, 2)
            return
        if user.debt > 0:
            cover = min(user.debt, delta)
            user.debt = round(user.debt - cover, 2)
            delta -= cover
        if delta > 0:
            user.balance = round(user.balance + delta, 2)

    async def subtract_with_debt(self, user_id: int, amount: float) -> float:
        """Списывает amount, при нехватке остаток уходит в debt. Возвращает фактический debt-прирост."""
        user = await self.get_by_id(user_id)
        if user is None or amount <= 0:
            return 0.0
        if user.balance >= amount:
            user.balance = round(user.balance - amount, 2)
            return 0.0
        shortfall = round(amount - user.balance, 2)
        user.balance = 0.0
        user.debt = round(user.debt + shortfall, 2)
        return shortfall

    async def inc_ref_count(self, user_id: int, delta: int = 1) -> None:
        await self.session.execute(
            update(User).where(User.id == user_id).values(ref_count=User.ref_count + delta)
        )

    async def inc_confirmed_ref_count(self, user_id: int, delta: int = 1) -> None:
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(confirmed_ref_count=User.confirmed_ref_count + delta)
        )

    async def list_subs_passed_sample(self, limit: int) -> list[User]:
        """Случайная выборка не-забаненных юзеров, прошедших гейт. Для sub_rechecker."""
        res = await self.session.execute(
            select(User)
            .where(
                User.subs_passed_at.is_not(None),
                User.is_banned.is_(False),
                User.is_deleted.is_(False),
            )
            .order_by(func.random())
            .limit(limit)
        )
        return list(res.scalars().all())

    async def joined_recently(self, days: int) -> int:
        """Сколько юзеров создано за последние N дней. Для админ-статистики (Этап 9)."""
        since = utcnow() - timedelta(days=days)
        res = await self.session.execute(
            select(func.count(User.id)).where(User.created_at >= since)
        )
        return int(res.scalar_one() or 0)

    # ---------- админка (Этап 9) ----------

    async def get_by_username(self, username: str) -> User | None:
        res = await self.session.execute(
            select(User).where(func.lower(User.username) == username.lower())
        )
        return res.scalar_one_or_none()

    async def counts_summary(self) -> dict[str, int]:
        """Сводные счётчики для дашборда."""
        total = await self.session.scalar(select(func.count(User.id)))
        passed = await self.session.scalar(
            select(func.count(User.id)).where(User.subs_passed_at.is_not(None))
        )
        banned = await self.session.scalar(
            select(func.count(User.id)).where(User.is_banned.is_(True))
        )
        shadow = await self.session.scalar(
            select(func.count(User.id)).where(User.is_shadow_banned.is_(True))
        )
        return {
            "total": int(total or 0),
            "passed": int(passed or 0),
            "banned": int(banned or 0),
            "shadow": int(shadow or 0),
        }

    async def balance_summary(self) -> dict[str, float]:
        """Сумма балансов и долгов (обязательства бота)."""
        balance = await self.session.scalar(select(func.coalesce(func.sum(User.balance), 0.0)))
        debt = await self.session.scalar(select(func.coalesce(func.sum(User.debt), 0.0)))
        return {"balance": round(float(balance or 0.0), 2), "debt": round(float(debt or 0.0), 2)}

    async def set_banned(self, user_id: int, banned: bool) -> None:
        await self.session.execute(
            update(User).where(User.id == user_id).values(is_banned=banned)
        )

    async def set_shadow_banned(self, user_id: int, shadow: bool) -> None:
        await self.session.execute(
            update(User).where(User.id == user_id).values(is_shadow_banned=shadow)
        )

    async def list_broadcast_tg_ids(self) -> list[int]:
        """Все tg_id для рассылки (живые, не забаненные)."""
        res = await self.session.execute(
            select(User.tg_id).where(
                User.is_banned.is_(False),
                User.is_deleted.is_(False),
            )
        )
        return [int(x) for x in res.scalars().all()]

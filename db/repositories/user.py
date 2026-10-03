from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import utcnow
from db.models import MoneyOperation, User
from db.money import MAX_UNITS, from_units, settlement_units
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
            now = utcnow()
            # Views and fast taps should not take SQLite's writer lock only for presence.
            previous = user.last_seen_at
            if previous is None or (now.replace(tzinfo=None) - previous.replace(tzinfo=None)).total_seconds() >= 60:
                user.last_seen_at = now
        return user, created

    async def mark_terms_accepted(self, tg_id: int) -> None:
        await self.session.execute(
            update(User).where(User.tg_id == tg_id).values(accepted_terms_at=utcnow())
        )

    async def mark_captcha_passed(self, tg_id: int) -> None:
        await self.session.execute(
            update(User).where(User.tg_id == tg_id).values(captcha_passed_at=utcnow())
        )

    async def mark_subs_passed(self, tg_id: int, at: datetime | None = None) -> bool:
        """Атомарно отмечает первое прохождение текущего subscription-gate."""
        result = await self.session.execute(
            update(User)
            .where(User.tg_id == tg_id, User.subs_passed_at.is_(None))
            .values(subs_passed_at=at or utcnow())
            .execution_options(synchronize_session="fetch")
        )
        return bool(result.rowcount)

    async def claim_partner_reward(self, user_id: int) -> bool:
        """Единожды резервирует CPA-награду за пользователя."""
        result = await self.session.execute(
            update(User)
            .where(User.id == user_id, User.partner_rewarded.is_(False))
            .values(partner_rewarded=True)
            .execution_options(synchronize_session="fetch")
        )
        return bool(result.rowcount)

    async def try_set_partner_attribution(
        self, user_id: int, *, partner_id: int, partner_link_id: int
    ) -> bool:
        """Атомарно фиксирует первую UTM-атрибуцию до прохождения gate."""
        result = await self.session.execute(
            update(User)
            .where(
                User.id == user_id,
                User.partner_id.is_(None),
                User.partner_link_id.is_(None),
                User.subs_passed_at.is_(None),
            )
            .values(partner_id=partner_id, partner_link_id=partner_link_id)
            .execution_options(synchronize_session="fetch")
        )
        return bool(result.rowcount)

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

    @staticmethod
    def reward_conditions():
        """Shared minimum admission policy; rechecked in the financial UPDATE."""
        return (User.is_banned.is_(False), User.is_shadow_banned.is_(False), User.is_deleted.is_(False))

    async def rewards_allowed(self, user_id: int) -> bool:
        return await self.session.scalar(select(User.id).where(User.id == user_id, *self.reward_conditions())) is not None

    async def lock_rewards_allowed(self, user_id: int) -> bool:
        """Admission + SQLite write claim, only after any external gate IO."""
        return await self._lock_account(user_id, conditions=self.reward_conditions()) is not None

    async def _lock_account(self, user_id: int, *, conditions=(), reference: str | None = None):
        conditions = list(conditions)
        if reference is not None:
            conditions.append(~select(MoneyOperation.id).where(MoneyOperation.reference == reference).exists())
        # First statement is a write: SQLite serializes account mutations before
        # we read balances. No Telegram network operation occurs in this method.
        result = await self.session.execute(
            update(User).where(User.id == user_id, *conditions)
            .values(balance_units=User.balance_units)
            .returning(User.balance_units, User.debt_units, User.reserved_units)
            .execution_options(synchronize_session=False)
        )
        return result.one_or_none()

    async def _record(self, user_id: int, old, new, *, reason: str, reference: str | None):
        if any(value < 0 or value > MAX_UNITS for value in new):
            raise ValueError("account amount outside storage bounds")
        balance, debt, reserved = new
        await self.session.execute(update(User).where(User.id == user_id).values(
            balance_units=balance, debt_units=debt, reserved_units=reserved
        ).execution_options(synchronize_session="fetch"))
        self.session.add(MoneyOperation(
            account_kind="user", user_id=user_id, reason=reason, reference=reference,
            balance_delta_units=balance-old[0], debt_delta_units=debt-old[1],
            reserved_delta_units=reserved-old[2], balance_after_units=balance,
            debt_after_units=debt, reserved_after_units=reserved,
        ))
        await self.session.flush()

    async def add_balance(self, user_id: int, delta, *, reason: str = "credit", reference: str | None = None) -> bool:
        """Exact credit under the old cent settlement rule; first pays debt."""
        amount = settlement_units(delta)
        if amount < 0:
            await self.subtract_with_debt(user_id, -from_units(amount), reason=reason, reference=reference)
            return True
        old = await self._lock_account(user_id, conditions=self.reward_conditions(), reference=reference)
        if old is None:
            return False
        if amount == 0:
            return True
        repaid = min(old[1], amount)
        await self._record(user_id, old, (old[0]+amount-repaid, old[1]-repaid, old[2]), reason=reason, reference=reference)
        return True

    async def subtract_with_debt(self, user_id: int, amount, *, reason: str = "debit", reference: str | None = None):
        """Reversal still applies to blocked users; never spends gift reserves."""
        units = settlement_units(amount)
        if units <= 0:
            return from_units(0)
        old = await self._lock_account(user_id, reference=reference)
        if old is None:
            return from_units(0)
        spent = min(old[0], units)
        shortfall = units-spent
        await self._record(user_id, old, (old[0]-spent, old[1]+shortfall, old[2]), reason=reason, reference=reference)
        return from_units(shortfall)

    async def try_spend_balance(self, user_id: int, amount, *, reason: str = "spend", reference: str | None = None) -> bool:
        units = settlement_units(amount)
        if units <= 0:
            return await self.rewards_allowed(user_id)
        old = await self._lock_account(user_id, conditions=(*self.reward_conditions(), User.debt_units == 0, User.balance_units >= units), reference=reference)
        if old is None:
            return False
        await self._record(user_id, old, (old[0]-units, old[1], old[2]), reason=reason, reference=reference)
        return True

    async def reserve(self, user_id: int, amount_units: int, *, reference: str) -> bool:
        if not isinstance(amount_units, int) or isinstance(amount_units, bool) or not 0 < amount_units <= MAX_UNITS:
            raise ValueError("reserve requires positive integer parts")
        key = f"reserve:{reference}"
        old = await self._lock_account(user_id, conditions=(*self.reward_conditions(), User.debt_units == 0, User.balance_units >= amount_units), reference=key)
        if old is None:
            return False
        await self._record(user_id, old, (old[0]-amount_units, old[1], old[2]+amount_units), reason="gift_reserve", reference=key)
        return True

    async def _finish_reserve(self, user_id: int, amount_units: int, *, reference: str, consume: bool) -> bool:
        if not isinstance(amount_units, int) or isinstance(amount_units, bool) or not 0 < amount_units <= MAX_UNITS:
            raise ValueError("reserve settlement requires positive integer parts")
        reserved = select(MoneyOperation.id).where(
            MoneyOperation.user_id == user_id,
            MoneyOperation.reference == f"reserve:{reference}",
            MoneyOperation.reserved_delta_units == amount_units,
        ).exists()
        terminal = select(MoneyOperation.id).where(MoneyOperation.reference.in_([f"release:{reference}", f"consume:{reference}"])).exists()
        reason = "gift_consume" if consume else "gift_release"
        key = f"{'consume' if consume else 'release'}:{reference}"
        old = await self._lock_account(user_id, conditions=(User.reserved_units >= amount_units, reserved, ~terminal), reference=key)
        if old is None:
            return False
        # A reversal may have created debt while the gift was pending. Refunds
        # settle that debt before increasing the spendable balance.
        repaid = 0 if consume else min(old[1], amount_units)
        new = (old[0] + (0 if consume else amount_units-repaid), old[1]-repaid, old[2]-amount_units)
        await self._record(user_id, old, new, reason=reason, reference=key)
        return True

    async def release_reserve(self, user_id: int, amount_units: int, *, reference: str) -> bool:
        return await self._finish_reserve(user_id, amount_units, reference=reference, consume=False)

    async def consume_reserve(self, user_id: int, amount_units: int, *, reference: str) -> bool:
        return await self._finish_reserve(user_id, amount_units, reference=reference, consume=True)

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

    async def joined_since(self, since: datetime) -> int:
        """Количество пользователей, созданных с указанного момента."""
        res = await self.session.execute(
            select(func.count(User.id)).where(User.created_at >= since)
        )
        return int(res.scalar_one() or 0)

    # ---------- админка (Этап 9) ----------

    async def get_by_username(self, username: str) -> User | None:
        res = await self.session.execute(
            select(User)
            .where(func.lower(User.username) == username.lower())
            .order_by(User.last_seen_at.desc().nullslast(), User.id.desc())
            .limit(1)
        )
        return res.scalars().first()

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
        balance = await self.session.scalar(select(func.coalesce(func.sum(User.balance_units), 0)))
        debt = await self.session.scalar(select(func.coalesce(func.sum(User.debt_units), 0)))
        reserved = await self.session.scalar(select(func.coalesce(func.sum(User.reserved_units), 0)))
        return {"balance": float(from_units(balance or 0)), "debt": float(from_units(debt or 0)),
                "reserved": float(from_units(reserved or 0)),
                "liability": float(from_units((balance or 0) + (reserved or 0)))}

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

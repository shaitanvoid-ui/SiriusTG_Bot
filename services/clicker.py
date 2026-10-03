"""Кликер: одна тапка = микро-награда. Лимит по уровню, rate-limit, мини-капча.

Состояние юзера на день — в `ClickerDay`. Один ряд на (user, day).
Все цифры — из settings:
    click.base_reward, click.min_interval_ms,
    click.captcha_every_min, click.captcha_every_max
Лимит и множитель — из текущего уровня юзера (LevelService).
"""

from __future__ import annotations

import random
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import ClickerDay, User
from db.money import decimal_amount, from_units, settlement_units
from db.repositories.action_log import ActionLogRepo
from db.repositories.clicker_day import ClickerDayRepo
from db.repositories.user import UserRepo
from services.level import LevelInfo, LevelService
from services.settings import SettingsService
from utils.captcha import EMOJI_POOL
from utils.tz import today_msk


CLICKER_HINT_COUNT: int = 3   # сколько эмодзи в подсказке
CLICKER_CHOICES_COUNT: int = 4  # сколько кнопок (3 из подсказки + 1 лишний)
SEP: str = "|"


class ClickStatus(StrEnum):
    BLOCKED = "blocked"
    OK = "ok"
    NEED_CAPTCHA = "need_captcha"
    TOO_FAST = "too_fast"
    DAILY_LIMIT = "daily_limit"


class CaptchaStatus(StrEnum):
    OK = "ok"
    WRONG = "wrong"
    EXPIRED = "expired"


@dataclass(frozen=True)
class ClickerView:
    """Срез состояния для отрисовки экрана кликера."""

    clicks: int
    daily_limit: int
    earned_today: float
    reward_per_click: float
    balance: float
    level: LevelInfo
    cooldown_ms_left: int
    captcha_required: bool
    captcha_hint: tuple[str, ...]
    captcha_choices: tuple[str, ...]
    captcha_token: str | None


@dataclass(frozen=True)
class ClickResult:
    status: ClickStatus
    reward: float = 0.0
    clicks: int = 0
    daily_limit: int = 0
    earned_today: float = 0.0
    balance: float = 0.0
    captcha_required: bool = False
    captcha_hint: tuple[str, ...] = ()
    captcha_choices: tuple[str, ...] = ()
    captcha_token: str | None = None
    retry_after_ms: int = 0


@dataclass(frozen=True)
class CaptchaSubmitResult:
    status: CaptchaStatus
    captcha_hint: tuple[str, ...] = ()
    captcha_choices: tuple[str, ...] = ()
    captcha_token: str | None = None


def _now_ms() -> int:
    return int(datetime.now(tz=timezone.utc).timestamp() * 1000)


def _today():
    """День кликера — московские сутки."""
    return today_msk()


def _gen_mini_captcha() -> tuple[str, tuple[str, ...], tuple[str, ...], str]:
    """Возвращает (answer, hint, choices, token)."""
    rng = random.SystemRandom()
    hint = tuple(rng.sample(EMOJI_POOL, CLICKER_HINT_COUNT))
    # лишний — не из подсказки
    pool_without = [e for e in EMOJI_POOL if e not in hint]
    answer = rng.choice(pool_without)
    choices_list = list(hint) + [answer]
    rng.shuffle(choices_list)
    return answer, hint, tuple(choices_list), secrets.token_urlsafe(12)


class ClickerService:
    def __init__(self, session: AsyncSession, settings_svc: SettingsService) -> None:
        self.session = session
        self.settings = settings_svc
        self.level_svc = LevelService(settings_svc)

    async def _econ(self, info: LevelInfo) -> tuple[float, int, int, int, int]:
        """(reward_per_click, daily_limit, min_interval_ms, captcha_min, captcha_max)."""
        base = await self.settings.get_float("click.base_reward", 0.01)
        min_interval = await self.settings.get_int("click.min_interval_ms", 250)
        cap_min = await self.settings.get_int("click.captcha_every_min", 20)
        cap_max = await self.settings.get_int("click.captcha_every_max", 30)
        if cap_max < cap_min:
            cap_max = cap_min
        reward = float(from_units(settlement_units(decimal_amount(base) * decimal_amount(info.click_mult))))
        daily_limit = int(info.click_daily_limit)
        return reward, daily_limit, min_interval, cap_min, cap_max

    async def _load_day(
        self, user: User, *, cap_min: int, cap_max: int
    ) -> ClickerDay:
        """Достаёт/создаёт ряд на сегодня, инициализирует threshold капчи."""
        repo = ClickerDayRepo(self.session)
        day_row = await repo.get_or_create(user.id, _today())
        if day_row.captcha_threshold <= 0:
            await repo.ensure_captcha_threshold(
                day_row.id, random.SystemRandom().randint(cap_min, cap_max)
            )
            await self.session.refresh(day_row)
        return day_row

    @staticmethod
    def _split(field: str | None) -> tuple[str, ...]:
        if not field:
            return ()
        return tuple(e for e in field.split(SEP) if e)

    async def get_view(self, user: User) -> ClickerView:
        info = await self.level_svc.compute(user.confirmed_ref_count)
        reward, daily_limit, min_interval, cap_min, cap_max = await self._econ(info)
        day_row = await self._load_day(user, cap_min=cap_min, cap_max=cap_max)

        cooldown_left = 0
        if day_row.last_click_ms > 0:
            diff = _now_ms() - day_row.last_click_ms
            if 0 <= diff < min_interval:
                cooldown_left = min_interval - diff

        return ClickerView(
            clicks=day_row.clicks,
            daily_limit=daily_limit,
            earned_today=round(day_row.earned, 2),
            reward_per_click=reward,
            balance=round(user.balance, 2),
            level=info,
            cooldown_ms_left=cooldown_left,
            captcha_required=day_row.captcha_token is not None,
            captcha_hint=self._split(day_row.captcha_hint),
            captcha_choices=self._split(day_row.captcha_choices),
            captcha_token=day_row.captcha_token,
        )

    async def click(self, user: User) -> ClickResult:
        if not await UserRepo(self.session).lock_rewards_allowed(user.id):
            return ClickResult(status=ClickStatus.BLOCKED, balance=round(user.balance, 2))
        info = await self.level_svc.compute(user.confirmed_ref_count)
        reward, daily_limit, min_interval, cap_min, cap_max = await self._econ(info)
        day_row = await self._load_day(user, cap_min=cap_min, cap_max=cap_max)

        # 1) ждёт капчу
        if day_row.captcha_token is not None:
            return ClickResult(
                status=ClickStatus.NEED_CAPTCHA,
                clicks=day_row.clicks,
                daily_limit=daily_limit,
                earned_today=round(day_row.earned, 2),
                balance=round(user.balance, 2),
                captcha_required=True,
                captcha_hint=self._split(day_row.captcha_hint),
                captcha_choices=self._split(day_row.captcha_choices),
                captcha_token=day_row.captcha_token,
            )

        # 2) лимит дня
        if day_row.clicks >= daily_limit:
            return ClickResult(
                status=ClickStatus.DAILY_LIMIT,
                clicks=day_row.clicks,
                daily_limit=daily_limit,
                earned_today=round(day_row.earned, 2),
                balance=round(user.balance, 2),
            )

        # 3) rate-limit
        now_ms = _now_ms()
        if day_row.last_click_ms > 0:
            diff = now_ms - day_row.last_click_ms
            if diff < min_interval:
                return ClickResult(
                    status=ClickStatus.TOO_FAST,
                    clicks=day_row.clicks,
                    daily_limit=daily_limit,
                    earned_today=round(day_row.earned, 2),
                    balance=round(user.balance, 2),
                    retry_after_ms=min_interval - diff,
                )

        # 4) Финальная проверка + запись одним UPDATE: повторный callback не
        # сможет одновременно пройти rate-limit или дневной лимит.
        clicked = await ClickerDayRepo(self.session).try_click(
            row_id=day_row.id,
            now_ms=now_ms,
            min_interval_ms=min_interval,
            daily_limit=daily_limit,
            reward=reward,
        )
        if not clicked:
            await self.session.refresh(day_row)
            if day_row.captcha_token is not None:
                return ClickResult(
                    status=ClickStatus.NEED_CAPTCHA,
                    clicks=day_row.clicks,
                    daily_limit=daily_limit,
                    earned_today=round(day_row.earned, 2),
                    balance=round(user.balance, 2),
                    captcha_required=True,
                    captcha_hint=self._split(day_row.captcha_hint),
                    captcha_choices=self._split(day_row.captcha_choices),
                    captcha_token=day_row.captcha_token,
                )
            if day_row.clicks >= daily_limit:
                return ClickResult(
                    status=ClickStatus.DAILY_LIMIT,
                    clicks=day_row.clicks,
                    daily_limit=daily_limit,
                    earned_today=round(day_row.earned, 2),
                    balance=round(user.balance, 2),
                )
            retry = max(0, min_interval - max(0, now_ms - day_row.last_click_ms))
            return ClickResult(
                status=ClickStatus.TOO_FAST,
                clicks=day_row.clicks,
                daily_limit=daily_limit,
                earned_today=round(day_row.earned, 2),
                balance=round(user.balance, 2),
                retry_after_ms=retry,
            )

        await self.session.refresh(day_row)
        await UserRepo(self.session).add_balance(user.id, reward, reason="click_reward")

        captcha_required = False
        captcha_hint: tuple[str, ...] = ()
        captcha_choices: tuple[str, ...] = ()
        captcha_token: str | None = None

        # 5) триггер мини-капчи
        if day_row.since_captcha >= max(1, day_row.captcha_threshold):
            answer, hint, choices, token = _gen_mini_captcha()
            day_row.captcha_token = token
            day_row.captcha_answer = answer
            day_row.captcha_hint = SEP.join(hint)
            day_row.captcha_choices = SEP.join(choices)
            day_row.since_captcha = 0
            day_row.captcha_threshold = random.SystemRandom().randint(cap_min, cap_max)
            captcha_required = True
            captcha_hint = hint
            captcha_choices = choices
            captcha_token = token

        await ActionLogRepo(self.session).log(
            user_tg_id=user.tg_id,
            action="click",
            payload={"reward": reward, "clicks": day_row.clicks},
        )

        # подтянуть свежий баланс юзера
        fresh_user = await UserRepo(self.session).get_by_id(user.id)
        balance = round(fresh_user.balance, 2) if fresh_user else round(user.balance + reward, 2)

        return ClickResult(
            status=ClickStatus.OK,
            reward=reward,
            clicks=day_row.clicks,
            daily_limit=daily_limit,
            earned_today=round(day_row.earned, 2),
            balance=balance,
            captcha_required=captcha_required,
            captcha_hint=captcha_hint,
            captcha_choices=captcha_choices,
            captcha_token=captcha_token,
        )

    async def submit_captcha(
        self, user: User, *, token: str, choice: str
    ) -> CaptchaSubmitResult:
        info = await self.level_svc.compute(user.confirmed_ref_count)
        _, _, _, cap_min, cap_max = await self._econ(info)
        day_row = await self._load_day(user, cap_min=cap_min, cap_max=cap_max)

        if day_row.captcha_token is None or day_row.captcha_token != token:
            return CaptchaSubmitResult(status=CaptchaStatus.EXPIRED)

        correct = day_row.captcha_answer
        if not correct:
            # битое состояние — сбросим, попросим начать заново
            day_row.captcha_token = None
            day_row.captcha_answer = None
            day_row.captcha_hint = None
            day_row.captcha_choices = None
            return CaptchaSubmitResult(status=CaptchaStatus.EXPIRED)

        if choice != correct:
            # перегенерим мини-капчу — даём вторую попытку без штрафа.
            answer, hint, choices, new_token = _gen_mini_captcha()
            day_row.captcha_token = new_token
            day_row.captcha_answer = answer
            day_row.captcha_hint = SEP.join(hint)
            day_row.captcha_choices = SEP.join(choices)
            await ActionLogRepo(self.session).log(
                user_tg_id=user.tg_id, action="click_captcha_wrong"
            )
            return CaptchaSubmitResult(
                status=CaptchaStatus.WRONG,
                captcha_hint=hint,
                captcha_choices=choices,
                captcha_token=new_token,
            )

        # ок — снимаем блок
        day_row.captcha_token = None
        day_row.captcha_answer = None
        day_row.captcha_hint = None
        day_row.captcha_choices = None
        await ActionLogRepo(self.session).log(
            user_tg_id=user.tg_id, action="click_captcha_ok"
        )
        return CaptchaSubmitResult(status=CaptchaStatus.OK)

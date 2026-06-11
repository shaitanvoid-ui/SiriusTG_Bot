"""Settings-сервис: чтение из БД с in-memory TTL-кэшем + seed дефолтов при старте.

Все цифры экономики (награды, лимиты, проценты) живут здесь, а не хардкодом в коде.
Это позволяет править их через админку без передеплоя.
"""

from __future__ import annotations

import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.repositories.setting import SettingRepo
from db.session import SessionLocal


log = get_logger(__name__)


# ---------- ключи и дефолты (единая точка истины) ----------

DEFAULTS: dict[str, tuple[Any, str]] = {
    # ---- рефералка ----
    "ref.reward": (3.0, "Награда рефереру за подтверждённого реферала, ⭐"),
    "ref.daily_limit": (0, "Лимит новых рефералов в сутки на одного юзера (0 — без лимита)"),
    "ref.maturation_days": (7, "Через сколько дней реф «созревает» (защита от отвалов снимается)"),
    # ---- вывод (Этап 7) ----
    "withdraw.min_amount": (15.0, "Минимальная сумма для вывода, ⭐"),
    "withdraw.min_confirmed_refs": (5, "Сколько подтверждённых рефов нужно для вывода"),
    "withdraw.per_day_limit": (5, "Максимум выводов в сутки на одного юзера"),
    # ---- sub-rechecker (Этап 3) ----
    "subrecheck.enabled": (True, "Включён ли воркер перепроверки подписок"),
    "subrecheck.interval_hours": (6, "Интервал запуска sub_rechecker, ч"),
    "subrecheck.sample_size": (50, "Размер случайной выборки за один прогон"),
    # ---- кликер (Этап 4) ----
    "click.base_reward": (0.1, "База за один клик, ⭐"),
    "click.daily_base_limit": (70, "Базовый дневной лимит кликов (Бронза)"),
    "click.min_interval_ms": (300000, "Минимальный интервал между кликами, мс (5 мин)"),
    "click.captcha_every_min": (20, "Мини-капча: минимум кликов между проверками"),
    "click.captcha_every_max": (30, "Мини-капча: максимум кликов между проверками"),
    # ---- задания (Этап 4) ----
    "tasks.enabled": (True, "Раздел опц. заданий включён"),
    # ---- пере-проверка опц. заданий (Этап 4, доводка) ----
    "tasks_recheck.enabled": (True, "Воркер пере-проверки выполненных опц. заданий"),
    "tasks_recheck.interval_min": (5, "Интервал пере-проверки заданий, мин"),
    "tasks_recheck.sample_size": (100, "Сколько completion за один прогон"),
    # ---- промокоды (Этап 4) ----
    "promo.max_code_length": (32, "Максимальная длина промокода"),
    # ---- бонус (Этап 5) ----
    "bonus.base": (0.5, "Базовый ежедневный бонус, ⭐"),
    "bonus.streak": (
        {"1": 0.5, "3": 0.7, "7": 1.0, "14": 1.5, "30": 2.0},
        "Streak: дни → размер бонуса",
    ),
    "bonus.bio_required": (True, "Требовать реф-ссылку в bio для ежедневного бонуса"),
    # ---- уровни ----
    # click_mult=1.0 везде (тап фиксированно = click.base_reward = 0.1⭐), лесенка
    # по click_daily_limit: дневной максимум с кликера растёт 4.0→10.0⭐ (шаг 1.5⭐).
    "levels.config": (
        [
            {"level": 1, "name": "Бронза",  "emoji": "🥉", "required_refs": 0,   "click_mult": 1.0, "click_daily_limit": 40},
            {"level": 2, "name": "Серебро", "emoji": "🥈", "required_refs": 5,   "click_mult": 1.0, "click_daily_limit": 55},
            {"level": 3, "name": "Золото",  "emoji": "🥇", "required_refs": 15,  "click_mult": 1.0, "click_daily_limit": 70},
            {"level": 4, "name": "Платина", "emoji": "💠", "required_refs": 50,  "click_mult": 1.0, "click_daily_limit": 85},
            {"level": 5, "name": "Алмаз",   "emoji": "💎", "required_refs": 150, "click_mult": 1.0, "click_daily_limit": 100},
        ],
        "Конфигурация уровней (порог по подтверждённым рефералам)",
    ),
    # ---- колесо фортуны (Этап 6) ----
    "wheel.enabled": (True, "Колесо фортуны включено"),
    "wheel.cost": (1.0, "Стоимость платного вращения, ⭐"),
    "wheel.free_per_day": (1, "Бесплатных вращений в сутки"),
    # Призы: список секторов {value, weight}. Матожидание держим < cost (дом в плюсе).
    "wheel.prizes": (
        [
            {"value": 0.0, "weight": 30},
            {"value": 0.01, "weight": 25},
            {"value": 0.05, "weight": 20},
            {"value": 0.1, "weight": 15},
            {"value": 0.5, "weight": 7},
            {"value": 1.0, "weight": 3},
        ],
        "Секторы колеса: значение приза (⭐) и вес",
    ),
    # ---- достижения (Этап 6) ----
    "achievements.enabled": (True, "Раздел достижений включён"),
    # metric ∈ {confirmed_refs, clicks_total, bonus_streak, tasks_done}
    "achievements.config": (
        [
            {"code": "ref10",   "name": "Командор",     "emoji": "🎖", "metric": "confirmed_refs", "threshold": 10,   "reward": 5.0},
            {"code": "ref50",   "name": "Магнат",       "emoji": "🏛", "metric": "confirmed_refs", "threshold": 50,   "reward": 25.0},
            {"code": "ref100",  "name": "Легенда",      "emoji": "👑", "metric": "confirmed_refs", "threshold": 100,  "reward": 60.0},
            {"code": "click500","name": "Кликер",       "emoji": "👆", "metric": "clicks_total",   "threshold": 500,  "reward": 2.0},
            {"code": "click5k", "name": "Молот",        "emoji": "🔨", "metric": "clicks_total",   "threshold": 5000, "reward": 10.0},
            {"code": "streak7", "name": "Неделя в деле","emoji": "🔥", "metric": "bonus_streak",   "threshold": 7,    "reward": 3.0},
            {"code": "streak30","name": "Железная воля","emoji": "⚡", "metric": "bonus_streak",   "threshold": 30,   "reward": 15.0},
            {"code": "tasks10", "name": "Исполнитель",  "emoji": "🎯", "metric": "tasks_done",     "threshold": 10,   "reward": 5.0},
        ],
        "Конфигурация достижений (метрика, порог, награда)",
    ),
    # ---- лидерборд (Этап 6) ----
    "leaderboard.enabled": (True, "Раздел Топ-100 включён"),
    "leaderboard.min_confirmed_refs": (10, "Минимум подтв. рефов для попадания в топ"),
    "leaderboard.display_size": (15, "Сколько строк показывать в карточке топа"),
    "leaderboard.payout_enabled": (True, "Воркер недельных выплат топу"),
    # Награды по местам: индекс 0 — 1-е место и т.д. (топ-10).
    "leaderboard.weekly_rewards": (
        [50.0, 30.0, 20.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0],
        "Награды топ-10 за неделю по местам, ⭐",
    ),
    # ---- бренд ----
    "brand.name": ("SIRIUS", "Имя бренда в шапке меню"),
    "brand.tagline": ("Stars Hub", "Подпись бренда в шапке меню"),
    "brand.utc_offset_hours": (3, "Смещение часового пояса для приветствия в меню (МСК = 3)"),
    "channel.url": ("", "Внешняя ссылка на канал проекта"),
    # ---- бэкапы и дайджест (Этап 13) ----
    "backup.enabled": (True, "Авто-бэкап БД в лог-канал"),
    "backup.interval_hours": (6, "Интервал бэкапа БД, ч"),
    "digest.enabled": (True, "Ежедневный дайджест метрик в лог-канал"),
    "digest.hour_utc": (9, "Час отправки дайджеста (UTC)"),
    # ---- партнёрская система (Этап 10) ----
    "partner.enabled": (True, "Партнёрская система включена"),
    "partner.reward_per_passed_user": (1.0, "⭐ партнёру за приведённого юзера, прошедшего онбординг"),
    "partner.percent_sponsor_reward": (50.0, "% партнёру от награды задания его спонсора"),
    "partner.min_payout_stars": (50.0, "Минимум ⭐ для партнёрской выплаты"),
    "partner.rub_per_star": (1.5, "Курс ⭐→₽ для партнёрских выплат"),
    "partner.max_links": (10, "Максимум UTM-ссылок у партнёра"),
    # ---- поддержка (Этап 11) ----
    "support.enabled": (True, "Раздел поддержки включён"),
    "support.max_tickets_per_hour": (3, "Антиспам: максимум новых обращений в час"),
    "support.autoclose_days": (7, "Автозакрытие тикета без ответа юзера, дней"),
    "support.autoclose_check_hours": (6, "Интервал проверки автозакрытия, ч"),
    "support.min_text_length": (10, "Минимум символов в обращении"),
    "support.max_text_length": (1500, "Максимум символов в обращении"),
    "support.faq": (
        [
            {
                "q": "Как заработать звёзды?",
                "a": "Все способы собраны в разделе «💎 Заработать»: приглашай друзей по личной ссылке, тапай в кликере, забирай ежедневный бонус, крути колесо и выполняй задания спонсоров. Способы суммируются.",
            },
            {
                "q": "Когда придёт награда за друга?",
                "a": "Сразу после того, как приглашённый пройдёт проверку и подпишется на каналы. Если он отпишется раньше срока — награда списывается обратно.",
            },
            {
                "q": "Зачем нужны уровни?",
                "a": "Уровень растёт с числом подтверждённых рефералов и поднимает твой дневной потолок в кликере. Прогресс виден в профиле.",
            },
            {
                "q": "Почему не начисляется бонус?",
                "a": "Бонус выдаётся один раз в день (по UTC). Если просишь повторно — загляни завтра. Стрик растёт за вход каждый день подряд и увеличивает награду.",
            },
            {
                "q": "Как вывести звёзды?",
                "a": "Звёзды копятся на балансе и обмениваются на подарки Telegram в разделе «💸 Вывод подарков». Следи за анонсами в нашем канале.",
            },
        ],
        "FAQ поддержки: список {q, a}",
    ),
    # ---- история операций (Этап 11) ----
    "history.page_size": (8, "Строк на страницу истории операций"),
    # ---- отзывы (Этап 8) ----
    "review.enabled": (True, "Раздел отзывов включён"),
    "review.reward": (1.0, "Награда за опубликованный отзыв, ⭐"),
    "review.antispam_min_refs": (3, "Минимум рефов для отзыва"),
    "review.antispam_cooldown_days": (7, "Минимум дней между отзывами"),
    "review.min_text_length": (30, "Минимум символов в отзыве"),
    "review.max_text_length": (500, "Максимум символов в отзыве"),
    "reviews_channel_id": ("", "ID канала для публикации отзывов (пусто = только в БД)"),
}


class SettingsService:
    """Async-обёртка над SettingRepo с TTL-кэшем."""

    def __init__(self, session: AsyncSession, *, ttl_sec: float = 60.0) -> None:
        self.session = session
        self.ttl = ttl_sec

    # in-process кэш — общий на всё приложение
    _cache: dict[str, tuple[float, Any]] = {}

    @classmethod
    def invalidate(cls, key: str | None = None) -> None:
        if key is None:
            cls._cache.clear()
        else:
            cls._cache.pop(key, None)

    async def get(self, key: str, default: Any = None) -> Any:
        now = time.monotonic()
        cached = self._cache.get(key)
        if cached is not None and (now - cached[0]) < self.ttl:
            return cached[1]
        value = await SettingRepo(self.session).get(key, default)
        self._cache[key] = (now, value)
        return value

    async def get_int(self, key: str, default: int) -> int:
        v = await self.get(key, default)
        try:
            return int(v)
        except (TypeError, ValueError):
            return default

    async def get_float(self, key: str, default: float) -> float:
        v = await self.get(key, default)
        try:
            return float(v)
        except (TypeError, ValueError):
            return default

    async def get_bool(self, key: str, default: bool) -> bool:
        v = await self.get(key, default)
        if isinstance(v, bool):
            return v
        if isinstance(v, (int, float)):
            return bool(v)
        if isinstance(v, str):
            return v.lower() in ("1", "true", "yes", "y", "on")
        return default

    async def get_str(self, key: str, default: str) -> str:
        v = await self.get(key, default)
        return str(v) if v is not None else default

    async def get_list(self, key: str, default: list[Any]) -> list[Any]:
        v = await self.get(key, default)
        return v if isinstance(v, list) else default

    async def get_dict(self, key: str, default: dict[str, Any]) -> dict[str, Any]:
        v = await self.get(key, default)
        return v if isinstance(v, dict) else default

    async def set(self, key: str, value: Any, description: str | None = None) -> None:
        await SettingRepo(self.session).set(key, value, description)
        self.invalidate(key)


async def seed_defaults() -> None:
    """Заполняет недостающие ключи дефолтами. Существующие — не трогает."""
    async with SessionLocal() as session:
        repo = SettingRepo(session)
        existing = {s.key for s in await repo.all()}
        added = 0
        for key, (value, desc) in DEFAULTS.items():
            if key in existing:
                continue
            await repo.set(key, value, desc)
            added += 1
        if added:
            await session.commit()
            log.info("settings_seeded", added=added)
        else:
            log.info("settings_seed_noop")

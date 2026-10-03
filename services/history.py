"""История операций (Этап 11): человеко-читаемая лента начислений/списаний.

Источник — ActionLog: берём только денежные действия (клики исключены —
70 строк по 0.1⭐ в день забили бы ленту). Сумма достаётся из payload.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import ActionLog, User
from db.repositories.action_log import ActionLogRepo
from services.settings import SettingsService
from utils.tz import fmt_dt

# action → (эмодзи, название). Сумма считается в _amount_of.
_RENDER: dict[str, tuple[str, str]] = {
    "bonus_claimed": ("🎁", "Бонус дня"),
    "wheel_spin": ("🎡", "Колесо фортуны"),
    "promo_redeem": ("🎟", "Промокод"),
    "task_done": ("🎯", "Задание выполнено"),
    "task_lost": ("🎯", "Задание отменено"),
    "ref_reward": ("👥", "Реферал подтверждён"),
    "ref_reward_lost": ("👥", "Реферал отвалился"),
    "leaderboard_payout": ("🏆", "Топ недели"),
    "achievement": ("🏅", "Достижение"),
    "admin_balance_delta": ("⚖️", "Корректировка баланса"),
}

HISTORY_ACTIONS: tuple[str, ...] = tuple(_RENDER)


@dataclass(frozen=True)
class HistoryEntry:
    emoji: str
    title: str
    amount: float  # знаковая: + начисление, − списание
    when: str      # «10.06 14:32» по Москве


@dataclass(frozen=True)
class HistoryPage:
    entries: list[HistoryEntry]
    page: int        # с 1
    total_pages: int  # минимум 1


def _payload_of(row: ActionLog) -> dict:
    if not row.payload:
        return {}
    try:
        data = json.loads(row.payload)
    except (TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _amount_of(action: str, payload: dict) -> float:
    """Знаковая сумма операции из payload."""
    try:
        if action == "wheel_spin":
            return float(payload.get("prize", 0.0)) - float(payload.get("cost", 0.0))
        if action == "admin_balance_delta":
            return float(payload.get("delta", 0.0))
        if action in ("task_lost", "ref_reward_lost"):
            return -float(payload.get("reward", payload.get("amount", 0.0)))
        return float(payload.get("reward", payload.get("amount", 0.0)))
    except (TypeError, ValueError):
        return 0.0


def _title_of(action: str, payload: dict) -> str:
    _, title = _RENDER[action]
    if action == "promo_redeem" and payload.get("code"):
        return f"{title} «{payload['code']}»"
    if action == "leaderboard_payout" and payload.get("rank"):
        return f"{title} · место {payload['rank']}"
    return title


class HistoryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.log_repo = ActionLogRepo(session)
        self.settings = SettingsService(session)

    async def page_for(self, user: User, page: int) -> HistoryPage:
        """Страница ленты (page с 1). Пустая лента — entries=[] и 1 страница."""
        # Защита и от старых/ручных значений в БД, созданных до появления
        # доменной валидации админки.
        page_size = min(50, max(1, await self.settings.get_int("history.page_size", 8)))

        total = await self.log_repo.count_for_user(user.tg_id, HISTORY_ACTIONS)
        total_pages = max(1, -(-total // page_size))
        page = max(1, min(page, total_pages))

        rows = await self.log_repo.list_page_for_user(
            user.tg_id,
            HISTORY_ACTIONS,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        entries = []
        for row in rows:
            payload = _payload_of(row)
            emoji, _ = _RENDER[row.action]
            entries.append(
                HistoryEntry(
                    emoji=emoji,
                    title=_title_of(row.action, payload),
                    amount=round(_amount_of(row.action, payload), 2),
                    when=fmt_dt(row.created_at),
                )
            )
        return HistoryPage(entries=entries, page=page, total_pages=total_pages)

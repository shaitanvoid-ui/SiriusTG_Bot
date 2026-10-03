"""support_autoclose: автозакрытие тикетов поддержки (Этап 11).

Тикет в статусе AWAITING (админ ответил) без реакции юзера дольше
`support.autoclose_days` закрывается автоматически с DM-уведомлением.
NEW/IN_PROGRESS не трогаем — они ждут админа, это его очередь.
"""

from __future__ import annotations

from contextlib import suppress
from datetime import timedelta

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from core.logger import get_logger
from db.base import utcnow
from db.repositories.support import TicketRepo
from db.repositories.user import UserRepo
from db.session import SessionLocal
from locales.ru import T
from services.settings import SettingsService
from services.support import SupportService

log = get_logger(__name__)


async def run_support_autoclose(bot: Bot) -> None:
    """Один прогон: найти просроченные AWAITING-тикеты → закрыть → DM."""
    notify: list[tuple[int, int]] = []  # (tg_id, ticket_id)
    closed = 0
    async with SessionLocal() as session:
        try:
            settings_svc = SettingsService(session)
            if not await settings_svc.get_bool("support.enabled", True):
                return
            days = await settings_svc.get_int("support.autoclose_days", 7)
            cutoff = utcnow() - timedelta(days=days)

            repo = TicketRepo(session)
            svc = SupportService(session)
            user_repo = UserRepo(session)
            for ticket in await repo.list_autoclose_candidates(cutoff):
                if not await svc.close(ticket, by="auto"):
                    continue
                closed += 1
                user = await user_repo.get_by_id(ticket.user_id)
                if user is not None:
                    notify.append((user.tg_id, ticket.id))
            await session.commit()
        except Exception:
            await session.rollback()
            log.exception("support_autoclose_failed")
            raise

    # уведомления — после успешного коммита
    for tg_id, ticket_id in notify:
        with suppress(TelegramAPIError):
            await bot.send_message(tg_id, T.notify_support_closed.format(id=ticket_id))
    if closed:
        log.info("support_autoclose_done", closed=closed)


def register_jobs(scheduler: AsyncIOScheduler, bot: Bot, *, interval_hours: int) -> None:
    scheduler.add_job(
        run_support_autoclose,
        IntervalTrigger(hours=max(1, interval_hours)),
        kwargs={"bot": bot},
        id="support_autoclose",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )

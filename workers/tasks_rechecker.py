"""tasks_rechecker: периодическая пере-проверка выполненных опц. заданий.

Юзер мог выполнить опц. задание (подписка на спонсора за награду), получить
звёзды и отписаться. sub_rechecker этим не занимается — он работает только с
обязательными спонсорами. Этот воркер закрывает дыру:

При отписке от опц. спонсора, по которому есть UserTaskCompletion:
  - списываем награду (UserRepo.subtract_with_debt, остаток уходит в долг)
  - удаляем UserTaskCompletion (повторная подписка снова откроет задание)
  - пишем ActionLog (task_lost)
  - уведомляем юзера (DM) и пишем сводку в лог-канал
"""

from __future__ import annotations

from contextlib import suppress

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from core.config import settings as app_settings
from core.logger import get_logger
from db.repositories.action_log import ActionLogRepo
from db.repositories.sponsor import SponsorRepo
from db.repositories.user import UserRepo
from db.repositories.user_subscription import UserSubscriptionRepo
from db.repositories.user_task_completion import UserTaskCompletionRepo
from db.session import SessionLocal
from locales.ru import T
from services.notifications import NotificationService
from services.settings import SettingsService
from services.sponsor import SponsorService
from utils.ui import stars


log = get_logger(__name__)


async def _notify_user(bot: Bot, tg_id: int, text: str) -> None:
    with suppress(TelegramAPIError):
        await bot.send_message(tg_id, text)


async def _notify_log_channel(bot: Bot, text: str) -> None:
    if app_settings.log_channel_id is None:
        return
    with suppress(TelegramAPIError):
        await bot.send_message(app_settings.log_channel_id, text)


async def _recheck_one(bot: Bot, *, completion_id: int) -> bool:
    """Возвращает True, если задание было потеряно (юзер отписался)."""
    async with SessionLocal() as session:
        try:
            comp_repo = UserTaskCompletionRepo(session)
            completion = await comp_repo.get_by_id(completion_id)
            if completion is None:
                await session.commit()
                return False

            sponsor_repo = SponsorRepo(session)
            user_repo = UserRepo(session)
            sponsor = await sponsor_repo.get(completion.sponsor_id)
            user = await user_repo.get_by_id(completion.user_id)
            if sponsor is None or user is None:
                await session.commit()
                return False

            sponsor_svc = SponsorService(sponsor_repo, UserSubscriptionRepo(session))
            is_sub = await sponsor_svc.check_one(bot, sponsor=sponsor, tg_id=user.tg_id)
            if is_sub:
                await session.commit()
                return False

            # отписался — фиксируем потерю до изменения строк
            tg_id = user.tg_id
            title = sponsor.title
            amount = round(completion.reward, 2)
            notify_allowed = NotificationService.is_enabled(user, "tasks")

            debt = await user_repo.subtract_with_debt(user.id, completion.reward)
            await comp_repo.delete(completion.id)
            await ActionLogRepo(session).log(
                user_tg_id=tg_id,
                action="task_lost",
                payload={"sponsor_id": sponsor.id, "reward": amount},
            )
            await session.commit()
        except Exception:
            await session.rollback()
            log.exception("tasks_rechecker_one_failed", completion_id=completion_id)
            return False

    # уведомления — после успешного коммита, не блокируем транзакцию IO-вызовами
    if notify_allowed:
        await _notify_user(
            bot, tg_id, T.notify_task_lost.format(title=title, amount=stars(amount))
        )
    await _notify_log_channel(
        bot,
        T.log_task_lost.format(
            tg_id=tg_id,
            title=title,
            amount=f"{amount:.2f}⭐",
            debt_part=f", в долг {debt:.2f}⭐" if debt > 0 else "",
        ),
    )
    return True


async def run_tasks_rechecker(bot: Bot) -> None:
    """Один прогон: выборка completion'ов → пере-проверка → отчёт."""
    async with SessionLocal() as session:
        settings_svc = SettingsService(session)
        enabled = await settings_svc.get_bool("tasks_recheck.enabled", True)
        if not enabled:
            return
        sample_size = await settings_svc.get_int("tasks_recheck.sample_size", 100)
        rows = await UserTaskCompletionRepo(session).list_sample(sample_size)
        completion_ids = [r.id for r in rows]

    if not completion_ids:
        return

    checked = 0
    lost = 0
    for completion_id in completion_ids:
        checked += 1
        if await _recheck_one(bot, completion_id=completion_id):
            lost += 1

    log.info("tasks_recheck_done", checked=checked, lost=lost)
    if lost > 0:
        await _notify_log_channel(
            bot, T.log_tasks_recheck_summary.format(checked=checked, lost=lost)
        )


def register_jobs(scheduler: AsyncIOScheduler, bot: Bot, *, interval_min: int) -> None:
    """Регистрирует джобу пере-проверки заданий. interval_min — из settings."""
    scheduler.add_job(
        run_tasks_rechecker,
        IntervalTrigger(minutes=max(1, interval_min)),
        kwargs={"bot": bot},
        id="tasks_rechecker",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )

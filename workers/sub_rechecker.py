"""sub_rechecker: периодическая перепроверка подписок прошедших гейт юзеров.

При отвале:
  - сбрасываем User.subs_passed_at
  - откатываем награду рефереру (ReferralService.on_user_lost_subs)
  - уведомляем самого юзера и реферера
  - пишем сводку в лог-канал

В этой же джобе крутим ReferralService.process_maturation —
закрепляем рефералов, которые пережили maturation-окно.
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
from db.session import SessionLocal
from locales.ru import T
from services.referral import ReferralService
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


async def _recheck_one(
    bot: Bot,
    *,
    tg_id: int,
    user_id: int,
) -> bool:
    """Возвращает True, если юзер отвалился."""
    async with SessionLocal() as session:
        try:
            sponsor_service = SponsorService(
                SponsorRepo(session), UserSubscriptionRepo(session)
            )
            all_ok, results = await sponsor_service.check_user(
                bot, tg_id=tg_id, user_id=user_id, force=True
            )
            if all_ok:
                await session.commit()
                return False
            if not any(result.is_definitively_not_subscribed for result in results):
                # Ошибка Telegram/API не является доказательством отписки.
                await session.commit()
                return False

            user_repo = UserRepo(session)
            user = await user_repo.get_by_id(user_id)
            if user is None:
                await session.commit()
                return False

            await user_repo.clear_subs_passed(tg_id)
            settings_svc = SettingsService(session)
            ref_svc = ReferralService(session, settings_svc)
            rollback = await ref_svc.on_user_lost_subs(user=user)
            await ActionLogRepo(session).log(
                user_tg_id=tg_id, action="subs_lost", payload={"via": "rechecker"}
            )
            await session.commit()
        except Exception:
            await session.rollback()
            log.exception("rechecker_one_failed", tg_id=tg_id)
            return False

    # уведомления — после успешного коммита, не блокируем транзакцию IO-вызовами
    await _notify_user(bot, tg_id, T.notify_self_subs_lost)
    if rollback is not None and rollback.amount > 0:
        if rollback.notify_allowed:
            debt_part = (
                T.notify_ref_lost_debt.format(debt=stars(rollback.debt))
                if rollback.debt > 0
                else ""
            )
            await _notify_user(
                bot,
                rollback.referrer_tg_id,
                T.notify_ref_lost.format(amount=stars(rollback.amount), debt_part=debt_part),
            )
        await _notify_log_channel(
            bot,
            T.log_ref_lost.format(
                referrer_tg_id=rollback.referrer_tg_id,
                amount=f"{rollback.amount:.2f}⭐",
                debt_part=f", в долг {rollback.debt:.2f}⭐" if rollback.debt > 0 else "",
            ),
        )
    return True


async def run_subrechecker(bot: Bot) -> None:
    """Один прогон: выборка → перепроверка → отчёт. Вызывается планировщиком."""
    async with SessionLocal() as session:
        settings_svc = SettingsService(session)
        enabled = await settings_svc.get_bool("subrecheck.enabled", True)
        sample_size = await settings_svc.get_int("subrecheck.sample_size", 50)
        if not enabled:
            return
        users = await UserRepo(session).list_subs_passed_sample(sample_size)
        targets = [(u.tg_id, u.id) for u in users]

    if not targets:
        return

    checked = 0
    lost = 0
    for tg_id, user_id in targets:
        checked += 1
        if await _recheck_one(bot, tg_id=tg_id, user_id=user_id):
            lost += 1

    log.info("subrecheck_done", checked=checked, lost=lost)
    if lost > 0:
        await _notify_log_channel(
            bot, T.log_subrecheck_summary.format(checked=checked, lost=lost)
        )


async def run_maturation() -> None:
    """Закрепление созревших рефералов. Отдельная джоба, лёгкая."""
    async with SessionLocal() as session:
        try:
            settings_svc = SettingsService(session)
            ref_svc = ReferralService(session, settings_svc)
            await ref_svc.process_maturation()
            await session.commit()
        except Exception:
            await session.rollback()
            log.exception("maturation_failed")
            raise


def register_jobs(scheduler: AsyncIOScheduler, bot: Bot, *, interval_hours: int) -> None:
    """Регистрирует обе джобы. interval_hours — из settings (на старте)."""
    scheduler.add_job(
        run_subrechecker,
        IntervalTrigger(hours=max(1, interval_hours)),
        kwargs={"bot": bot},
        id="sub_rechecker",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    scheduler.add_job(
        run_maturation,
        IntervalTrigger(hours=1),
        id="ref_maturation",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )

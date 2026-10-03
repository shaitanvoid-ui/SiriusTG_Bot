"""leaderboard_payout: еженедельные авто-награды топу по рефералам.

Раз в неделю (понедельник 00:05 UTC) награждаем топ по подтверждённым рефералам
за последние 7 дней. Награды по местам — из settings `leaderboard.weekly_rewards`.
Идемпотентность по ISO-неделе: `LeaderboardPayout` UQ(week_key, user) + проверка
наличия любой выплаты за неделю перед прогоном.
"""

from __future__ import annotations

from contextlib import suppress
from datetime import datetime, timezone

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from core.config import settings as app_settings
from core.logger import get_logger
from db.repositories.action_log import ActionLogRepo
from db.repositories.leaderboard_payout import LeaderboardPayoutRepo
from db.repositories.user import UserRepo
from db.money import from_units, settlement_units
from db.session import SessionLocal
from locales.ru import T
from services.leaderboard import period_since
from services.notifications import NotificationService
from services.settings import SettingsService
from utils.ui import stars


log = get_logger(__name__)

_DEFAULT_REWARDS: list[float] = [50.0, 30.0, 20.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0]


def week_key(now: datetime | None = None) -> str:
    iso = (now or datetime.now(tz=timezone.utc)).isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


async def _notify_user(bot: Bot, tg_id: int, text: str) -> None:
    with suppress(TelegramAPIError):
        await bot.send_message(tg_id, text)


async def _notify_log_channel(bot: Bot, text: str) -> None:
    if app_settings.log_channel_id is None:
        return
    with suppress(TelegramAPIError):
        await bot.send_message(app_settings.log_channel_id, text)


async def run_leaderboard_payout(bot: Bot) -> None:
    """Один прогон: топ недели → начисления → уведомления. Идемпотентен по неделе."""
    payouts: list[tuple[int, int, float, bool]] = []  # (tg_id, rank, amount, notify)
    wk = week_key()

    async with SessionLocal() as session:
        try:
            settings_svc = SettingsService(session)
            if not await settings_svc.get_bool("leaderboard.payout_enabled", True):
                return

            payout_repo = LeaderboardPayoutRepo(session)
            if await payout_repo.exists_for_week(wk):
                return  # уже выплачено на этой неделе

            rewards = await settings_svc.get_list(
                "leaderboard.weekly_rewards", _DEFAULT_REWARDS
            )
            rewards = [float(from_units(settlement_units(r))) for r in rewards]
            if not rewards:
                return
            min_conf = await settings_svc.get_int("leaderboard.min_confirmed_refs", 10)

            from db.repositories.referral import ReferralRepo

            rows = await ReferralRepo(session).leaderboard(
                since=period_since("week"), limit=len(rewards), min_confirmed=min_conf
            )
            if not rows:
                return

            user_repo = UserRepo(session)
            for idx, (ru_id, score, tg_id, _fname, _uname) in enumerate(rows):
                reward = rewards[idx] if idx < len(rewards) else 0.0
                if reward <= 0:
                    continue
                if not await user_repo.add_balance(ru_id, reward, reason="leaderboard_reward", reference=f"leaderboard:{wk}:{ru_id}"):
                    continue
                await payout_repo.create(
                    week_key=wk, user_id=ru_id, rank=idx + 1, amount=reward
                )
                await ActionLogRepo(session).log(
                    user_tg_id=tg_id,
                    action="leaderboard_payout",
                    payload={"week": wk, "rank": idx + 1, "amount": reward, "score": score},
                )
                winner = await user_repo.get_by_id(ru_id)
                notify = winner is None or NotificationService.is_enabled(winner, "rewards")
                payouts.append((tg_id, idx + 1, round(reward, 2), notify))
            await session.commit()
        except Exception:
            await session.rollback()
            log.exception("leaderboard_payout_failed", week=wk)
            raise

    # уведомления — после коммита, не блокируем транзакцию IO-вызовами
    for tg_id, rank, amount, notify in payouts:
        if notify:
            await _notify_user(
                bot, tg_id, T.notify_top_reward.format(rank=rank, amount=stars(amount))
            )
    if payouts:
        log.info("leaderboard_payout_done", week=wk, count=len(payouts))
        await _notify_log_channel(
            bot, T.log_top_payout.format(week=wk, count=len(payouts))
        )


def register_jobs(scheduler: AsyncIOScheduler, bot: Bot) -> None:
    """Еженедельный прогон: понедельник 00:05 UTC. Идемпотентность — по неделе."""
    scheduler.add_job(
        run_leaderboard_payout,
        CronTrigger(day_of_week="mon", hour=0, minute=5, timezone="UTC"),
        kwargs={"bot": bot},
        id="leaderboard_payout",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )

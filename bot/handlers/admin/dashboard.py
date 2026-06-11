"""Админка: дашборд (метрики) и система (воркеры/userbot/канал). Этап 9."""

from __future__ import annotations

from contextlib import suppress

from aiogram import F, Router, html
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.filters.admin import IsAdmin
from bot.keyboards.admin_panel import kb_dash
from core.config import settings as app_settings
from locales.ru import T
from services.admin_stats import AdminStatsService
from services.settings import SettingsService
from utils.ui import stars


router = Router(name="admin_dashboard")
router.callback_query.filter(IsAdmin())


@router.callback_query(F.data == "adm:dash")
async def cb_dash(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.message is None:
        await callback.answer()
        return
    s = await AdminStatsService(session).dashboard()
    text = T.admin_dash.format(
        users_total=s.users_total,
        users_passed=s.users_passed,
        users_new_today=s.users_new_today,
        users_banned=s.users_banned,
        users_shadow=s.users_shadow,
        balance_total=stars(s.balance_total),
        debt_total=stars(s.debt_total),
        clicks_today=s.clicks_today,
        bonuses_today=s.bonuses_today,
        spins_today=s.spins_today,
        tasks_today=s.tasks_today,
        refs_today=s.refs_today,
        reviews_pending=s.reviews_pending,
    )
    with suppress(Exception):
        await callback.message.edit_text(text, reply_markup=kb_dash("adm:dash"))
    await callback.answer()


@router.callback_query(F.data == "adm:sys")
async def cb_sys(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.message is None:
        await callback.answer()
        return
    settings_svc = SettingsService(session)
    sub_interval = await settings_svc.get_int("subrecheck.interval_hours", 6)
    tasks_interval = await settings_svc.get_int("tasks_recheck.interval_min", 5)
    channel_url = await settings_svc.get_str("channel.url", "")

    userbot_configured = bool(app_settings.tg_api_id and app_settings.tg_api_hash)
    userbot_state = T.admin_userbot_on if userbot_configured else T.admin_userbot_off
    channel_state = (
        f"<b>{html.quote(channel_url)}</b>" if channel_url else T.admin_channel_unset
    )
    log_channel = (
        f"<code>{app_settings.log_channel_id}</code>"
        if app_settings.log_channel_id
        else "<i>не настроен</i>"
    )

    text = T.admin_system.format(
        sub_interval=sub_interval,
        tasks_interval=tasks_interval,
        userbot_state=userbot_state,
        channel_state=channel_state,
        log_channel=log_channel,
    )
    with suppress(Exception):
        await callback.message.edit_text(text, reply_markup=kb_dash("adm:sys"))
    await callback.answer()

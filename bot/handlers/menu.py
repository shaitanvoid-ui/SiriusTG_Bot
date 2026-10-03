"""Главное меню — премиум inline-панель с edit-in-place навигацией."""

from __future__ import annotations

from utils.telegram import ignore_unchanged

from contextlib import suppress

from aiogram import F, Router, html
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.types import InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.main_menu import kb_main_menu
from db.models import User
from db.repositories.user import UserRepo
from locales.ru import T
from services.settings import SettingsService
from services.dashboard import DashboardService
from utils.tz import now_msk
from utils.ui import brand_header, count_ru, html_text, progress_bar, stars


router = Router(name="menu")


def greeting_for_hour(hour: int) -> str:
    if 5 <= hour < 12:
        return T.greeting_morning
    if 12 <= hour < 18:
        return T.greeting_day
    if 18 <= hour < 23:
        return T.greeting_evening
    return T.greeting_night


def _greeting() -> str:
    """Приветствие по московскому времени."""
    return greeting_for_hour(now_msk().hour)


# ---------- core renderer ----------

async def _build_caption(session: AsyncSession, user: User) -> tuple[str, InlineKeyboardMarkup]:
    settings_svc = SettingsService(session)
    await settings_svc.preload()

    brand_name = await settings_svc.get_str("brand.name", "SIRIUS")
    brand_tagline = await settings_svc.get_str("brand.tagline", "Stars Hub")
    channel_url = await settings_svc.get_str("channel.url", "")
    ref_reward = await settings_svc.get_float("ref.reward", 3.0)

    view = await DashboardService(session, settings_svc).get_view(user)
    info = view.level
    bar = progress_bar(info.progress_current, info.progress_total)
    if info.is_max:
        progress_text = T.menu_progress_max
    else:
        progress_text = T.menu_progress_to_next.format(
            next_name=html_text(info.next_name or ""),
            to_next_text=count_ru(info.to_next, "реферал", "реферала", "рефералов"),
        )

    name = html.quote(user.first_name or "друг")
    caption = T.menu_caption.format(
        brand=brand_header(html_text(brand_name), html_text(brand_tagline)),
        greeting=_greeting(),
        name=name,
        balance=stars(user.balance),
        level_emoji=html_text(info.emoji),
        level_name=html_text(info.name),
        confirmed_refs=user.confirmed_ref_count,
        progress_bar=bar,
        progress_text=progress_text,
        ref_reward=stars(ref_reward),
        today_hint=html_text(view.next_action.detail),
        today_action=html_text(view.next_action.label),
    )
    action = view.next_action
    return caption, kb_main_menu(channel_url=channel_url or None,
                                next_label=action.label, next_callback=action.callback)


async def render_main_menu_message(message: Message, session: AsyncSession, user: User) -> None:
    """Отрисовка как нового сообщения (после онбординга или /start уже-прошедшему)."""
    caption, keyboard = await _build_caption(session, user)
    await message.answer(caption, reply_markup=keyboard)


async def edit_to_main_menu(message: Message, session: AsyncSession, user: User) -> None:
    """Edit-in-place возврат в меню из дочернего раздела."""
    caption, keyboard = await _build_caption(session, user)
    with ignore_unchanged():
        await message.edit_text(caption, reply_markup=keyboard)


# ---------- callbacks ----------

@router.callback_query(F.data == "nav:menu")
async def cb_back_to_menu(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    db_user: User | None = None,
) -> None:
    if callback.message is None or callback.from_user is None:
        await callback.answer()
        return
    await state.clear()
    user = db_user or await UserRepo(session).get_by_tg_id(callback.from_user.id)
    if user is None:
        await callback.answer()
        return
    await edit_to_main_menu(callback.message, session, user)
    await callback.answer()


@router.callback_query(F.data == "nav:close")
async def cb_close(callback: CallbackQuery) -> None:
    if callback.message is not None:
        with suppress(TelegramBadRequest):
            await callback.message.delete()
    await callback.answer()


@router.callback_query(F.data == "feat:soon:channel")
async def cb_channel_unset(callback: CallbackQuery) -> None:
    await callback.answer(T.channel_unset_alert, show_alert=True)


@router.callback_query(F.data.startswith("feat:soon"))
async def cb_soon(callback: CallbackQuery) -> None:
    await callback.answer(T.soon_alert, show_alert=False)

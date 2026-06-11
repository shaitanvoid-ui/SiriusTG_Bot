"""Админка: канал проекта (доделка Этапа 8).

Установка @username публичного канала:
  - проверяем, что бот — админ канала (иначе не сможет проверять подписки);
  - пишем `channel.url` в settings (кнопка в главном меню);
  - автоматически создаём/реактивируем обязательного спонсора.
"""

from __future__ import annotations

import re
from contextlib import suppress

from aiogram import Bot, F, Router, html
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.filters.admin import IsAdmin
from bot.keyboards.admin_panel import kb_channel
from bot.states.admin import SetChannelStates
from db.models import SponsorKind
from db.repositories.sponsor import SponsorRepo
from locales.ru import T
from services.settings import SettingsService


router = Router(name="admin_channel")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

USERNAME_RE = re.compile(r"^@?([A-Za-z][A-Za-z0-9_]{3,31})$")


async def _render_card(message, session: AsyncSession) -> None:
    url = await SettingsService(session).get_str("channel.url", "")
    current = f"<b>{html.quote(url)}</b>" if url else T.admin_channel_unset
    with suppress(Exception):
        await message.edit_text(
            T.admin_channel_card.format(current=current), reply_markup=kb_channel()
        )


@router.callback_query(F.data == "adm:ch")
async def cb_open(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.message is None:
        await callback.answer()
        return
    await state.set_state(SetChannelStates.waiting_channel)
    await _render_card(callback.message, session)
    await callback.answer()


@router.message(SetChannelStates.waiting_channel, F.text)
async def msg_set_channel(
    message: Message, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    m = USERNAME_RE.match((message.text or "").strip())
    if m is None:
        await message.answer(T.admin_channel_invalid)
        return
    username = m.group(1)

    # канал существует и бот в нём админ?
    try:
        chat = await bot.get_chat(f"@{username}")
        member = await bot.get_chat_member(chat.id, bot.id)
        if member.status not in ("administrator", "creator"):
            await message.answer(T.addsp_bot_not_admin)
            return
    except TelegramAPIError:
        await message.answer(T.admin_channel_invalid)
        return

    title = chat.title or username

    # settings: кнопка «Наш канал» в меню
    settings_svc = SettingsService(session)
    await settings_svc.set("channel.url", f"https://t.me/{username}")

    # авто-добавление обязательным спонсором (или реактивация существующего)
    repo = SponsorRepo(session)
    sponsor = await repo.get_by_username(username) or (
        await repo.get_by_chat_id(chat.id) if chat.id else None
    )
    if sponsor is None:
        await repo.create(
            kind=SponsorKind.PUBLIC,
            title=title,
            chat_id=chat.id,
            username=username,
            is_required=True,
            is_active=True,
        )
    else:
        sponsor.is_required = True
        sponsor.is_active = True
        sponsor.title = title
        sponsor.chat_id = chat.id

    await state.clear()
    await message.answer(
        T.admin_channel_set.format(title=html.quote(title)), reply_markup=kb_channel()
    )

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
CHANNEL_URL_RE = re.compile(
    r"^https?://(?:www\.)?t\.me/([A-Za-z][A-Za-z0-9_]{3,31})/?$",
    re.IGNORECASE,
)


def _username_from_channel_url(url: str) -> str | None:
    match = CHANNEL_URL_RE.fullmatch(url.strip())
    return match.group(1) if match is not None else None


async def _render_card(message, session: AsyncSession) -> None:
    url = await SettingsService(session).get_str("channel.url", "")
    current = f"<b>{html.quote(url)}</b>" if url else T.admin_channel_unset
    with suppress(TelegramAPIError):
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

    canonical_username = (getattr(chat, "username", None) or username).lstrip("@")
    title = chat.title or canonical_username

    # settings: кнопка «Наш канал» в меню
    settings_svc = SettingsService(session)
    old_channel_url = await settings_svc.get_str("channel.url", "")

    # авто-добавление обязательным спонсором (или реактивация существующего)
    repo = SponsorRepo(session)
    sponsor = (await repo.get_by_chat_id(chat.id) if chat.id else None) or (
        await repo.get_by_username(canonical_username)
    )

    old_username = _username_from_channel_url(old_channel_url)
    old_sponsor = await repo.get_by_username(old_username) if old_username else None
    if old_sponsor is not None and (sponsor is None or old_sponsor.id != sponsor.id):
        old_sponsor.is_required = False
        old_sponsor.is_active = False

    if sponsor is None:
        sponsor = await repo.create(
            kind=SponsorKind.PUBLIC,
            title=title,
            chat_id=chat.id,
            username=canonical_username,
            is_required=True,
            is_active=True,
        )
    else:
        sponsor.is_required = True
        sponsor.is_active = True
        sponsor.title = title
        sponsor.chat_id = chat.id
        sponsor.username = canonical_username

    await settings_svc.set("channel.url", f"https://t.me/{canonical_username}")

    await state.clear()
    await message.answer(
        T.admin_channel_set.format(title=html.quote(title)), reply_markup=kb_channel()
    )

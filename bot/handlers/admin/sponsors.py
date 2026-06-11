from __future__ import annotations

import re
from contextlib import suppress

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.filters.admin import IsAdmin
from bot.keyboards.admin import (
    kb_add_cancel,
    kb_add_kind,
    kb_admin_root,
    kb_sponsor_card,
    kb_sponsor_delete_confirm,
    kb_sponsors_list,
)
from bot.states.admin import AddSponsorStates, EditSponsorStates
from db.models import Sponsor, SponsorKind
from db.repositories.sponsor import SponsorRepo
from locales.ru import T


router = Router(name="admin")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


INVITE_RE = re.compile(r"^https?://t\.me/(?:joinchat/|\+)[A-Za-z0-9_\-]+$")
USERNAME_RE = re.compile(r"^@?([A-Za-z][A-Za-z0-9_]{3,31})$")


# ---------- entrypoint ----------

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(T.admin_root, reply_markup=kb_admin_root())


@router.callback_query(F.data == "adm:root")
async def cb_root(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if callback.message is not None:
        with suppress(Exception):
            await callback.message.edit_text(T.admin_root, reply_markup=kb_admin_root())
    await callback.answer()


@router.callback_query(F.data == "adm:noop")
async def cb_noop(callback: CallbackQuery) -> None:
    await callback.answer("🛠 Скоро", show_alert=False)


# ---------- sponsors list ----------

async def _render_sponsors_list(callback: CallbackQuery, session: AsyncSession) -> None:
    sponsors = await SponsorRepo(session).list_all()
    total = len(sponsors)
    active = sum(1 for s in sponsors if s.is_active)
    required = sum(1 for s in sponsors if s.is_required and s.is_active)
    count_line = (
        T.admin_sponsors_count.format(total=total, active=active, required=required)
        if total else T.admin_sponsors_empty
    )
    text = T.admin_sponsors_root.format(count_line=count_line)
    if callback.message is not None:
        with suppress(Exception):
            await callback.message.edit_text(text, reply_markup=kb_sponsors_list(sponsors))


@router.callback_query(F.data == "adm:sponsors:list")
async def cb_sponsors_list(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    await state.clear()
    await _render_sponsors_list(callback, session)
    await callback.answer()


# ---------- sponsor card ----------

def _format_card(s: Sponsor) -> str:
    kind = T.admin_sponsor_kind_private if s.kind == SponsorKind.PRIVATE.value else T.admin_sponsor_kind_public
    status = T.admin_sponsor_status_active if s.is_active else T.admin_sponsor_status_paused
    required = T.admin_sponsor_required_yes if s.is_required else T.admin_sponsor_required_no
    if s.username:
        ident = f"Идентификатор: <code>@{s.username}</code>\n"
    elif s.chat_id is not None:
        ident = f"Идентификатор: <code>{s.chat_id}</code>\n"
    else:
        ident = "Идентификатор: <i>invite-link</i>\n"
    limit_part = f" / лимит {s.subs_limit}" if s.subs_limit else ""
    stats_line = T.admin_sponsor_stats.format(counter=s.subs_counter, limit_part=limit_part)
    return T.admin_sponsor_card.format(
        title=s.title,
        id=s.id,
        kind=kind,
        ident_line=ident,
        status=status,
        required=required,
        stats_line=stats_line,
    )


async def _render_card(callback: CallbackQuery, sponsor: Sponsor) -> None:
    if callback.message is not None:
        with suppress(Exception):
            await callback.message.edit_text(
                _format_card(sponsor),
                reply_markup=kb_sponsor_card(sponsor),
                disable_web_page_preview=True,
            )


@router.callback_query(F.data.startswith("adm:sp:open:"))
async def cb_sponsor_open(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    sid = _parse_id(callback.data)
    if sid is None:
        await callback.answer()
        return
    sponsor = await SponsorRepo(session).get(sid)
    if sponsor is None:
        await callback.answer(T.admin_sponsor_deleted, show_alert=True)
        await _render_sponsors_list(callback, session)
        return
    await _render_card(callback, sponsor)
    await callback.answer()


@router.callback_query(F.data.startswith("adm:sp:toggle_active:"))
async def cb_toggle_active(callback: CallbackQuery, session: AsyncSession) -> None:
    sid = _parse_id(callback.data)
    if sid is None:
        await callback.answer()
        return
    repo = SponsorRepo(session)
    s = await repo.get(sid)
    if s is None:
        await callback.answer(T.admin_sponsor_deleted, show_alert=True)
        return
    await repo.set_active(sid, not s.is_active)
    s = await repo.get(sid)
    await callback.answer(
        T.admin_sponsor_toggled_on if s.is_active else T.admin_sponsor_toggled_off
    )
    await _render_card(callback, s)


@router.callback_query(F.data.startswith("adm:sp:toggle_req:"))
async def cb_toggle_required(callback: CallbackQuery, session: AsyncSession) -> None:
    sid = _parse_id(callback.data)
    if sid is None:
        await callback.answer()
        return
    repo = SponsorRepo(session)
    s = await repo.get(sid)
    if s is None:
        await callback.answer(T.admin_sponsor_deleted, show_alert=True)
        return
    s.is_required = not s.is_required
    await session.flush()
    await callback.answer(T.admin_sponsor_required_toggled)
    await _render_card(callback, s)


@router.callback_query(F.data.startswith("adm:sp:del_ask:"))
async def cb_delete_ask(callback: CallbackQuery, session: AsyncSession) -> None:
    sid = _parse_id(callback.data)
    if sid is None:
        await callback.answer()
        return
    sponsor = await SponsorRepo(session).get(sid)
    if sponsor is None:
        await callback.answer(T.admin_sponsor_deleted, show_alert=True)
        return
    if callback.message is not None:
        with suppress(Exception):
            await callback.message.edit_text(
                _format_card(sponsor) + "\n\n<b>Удалить этого спонсора?</b>",
                reply_markup=kb_sponsor_delete_confirm(sid),
            )
    await callback.answer()


@router.callback_query(F.data.startswith("adm:sp:del_yes:"))
async def cb_delete_yes(callback: CallbackQuery, session: AsyncSession) -> None:
    sid = _parse_id(callback.data)
    if sid is None:
        await callback.answer()
        return
    await SponsorRepo(session).delete(sid)
    await callback.answer(T.admin_sponsor_deleted)
    await _render_sponsors_list(callback, session)


# ---------- add wizard ----------

@router.callback_query(F.data == "adm:sp:add")
async def cb_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(AddSponsorStates.waiting_kind)
    if callback.message is not None:
        with suppress(Exception):
            await callback.message.edit_text(T.addsp_step1, reply_markup=kb_add_kind())
    await callback.answer()


@router.callback_query(F.data == "adm:sp:add_cancel")
async def cb_add_cancel(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    await callback.answer(T.addsp_cancelled)
    await _render_sponsors_list(callback, session)


@router.callback_query(
    AddSponsorStates.waiting_kind,
    F.data.startswith("adm:sp:add_kind:"),
)
async def cb_add_kind(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.data is None or callback.message is None:
        await callback.answer()
        return
    kind = callback.data.split(":")[-1]
    await state.update_data(kind=kind)
    if kind == SponsorKind.PUBLIC.value:
        await state.set_state(AddSponsorStates.waiting_chat)
        with suppress(Exception):
            await callback.message.edit_text(T.addsp_step2_public, reply_markup=kb_add_cancel())
    else:
        await state.set_state(AddSponsorStates.waiting_invite)
        with suppress(Exception):
            await callback.message.edit_text(T.addsp_step2_private, reply_markup=kb_add_cancel())
    await callback.answer()


async def _resolve_public_chat(
    bot: Bot, message: Message
) -> tuple[int | None, str | None, str | None]:
    fwd = message.forward_from_chat
    if fwd is not None and fwd.type in ("channel", "supergroup"):
        return fwd.id, fwd.username, fwd.title or fwd.username
    if message.text is None:
        return None, None, None
    m = USERNAME_RE.match(message.text.strip())
    if m is None:
        return None, None, None
    uname = m.group(1)
    try:
        chat = await bot.get_chat(f"@{uname}")
    except (TelegramBadRequest, TelegramAPIError):
        return None, uname, None
    return chat.id, chat.username or uname, chat.title or uname


@router.message(AddSponsorStates.waiting_chat)
async def msg_chat(message: Message, state: FSMContext, bot: Bot) -> None:
    chat_id, username, title = await _resolve_public_chat(bot, message)
    if chat_id is None:
        await message.answer(T.addsp_chat_invalid, reply_markup=kb_add_cancel())
        return
    try:
        me = await bot.get_me()
        member = await bot.get_chat_member(chat_id=chat_id, user_id=me.id)
        if member.status not in ("administrator", "creator"):
            await message.answer(T.addsp_bot_not_admin, reply_markup=kb_add_cancel())
            return
    except TelegramAPIError:
        await message.answer(T.addsp_bot_not_admin, reply_markup=kb_add_cancel())
        return
    await state.update_data(chat_id=chat_id, username=username, suggested_title=title)
    await state.set_state(AddSponsorStates.waiting_title)
    hint = f"\n\nПодсказка: <b>{title}</b>" if title else ""
    await message.answer(T.addsp_step3 + hint, reply_markup=kb_add_cancel())


@router.message(AddSponsorStates.waiting_invite)
async def msg_invite(message: Message, state: FSMContext) -> None:
    if message.text is None or not INVITE_RE.match(message.text.strip()):
        await message.answer(T.addsp_invite_invalid, reply_markup=kb_add_cancel())
        return
    await state.update_data(invite_link=message.text.strip())
    await state.set_state(AddSponsorStates.waiting_private_forward)
    await message.answer(T.addsp_step2b_private, reply_markup=kb_add_cancel())


@router.message(AddSponsorStates.waiting_private_forward)
async def msg_private_forward(message: Message, state: FSMContext, bot: Bot) -> None:
    fwd = message.forward_from_chat
    if fwd is None or fwd.type not in ("channel", "supergroup"):
        await message.answer(T.addsp_private_forward_invalid, reply_markup=kb_add_cancel())
        return
    # бот должен быть админом — иначе проверять подписки не сможет
    try:
        me = await bot.get_me()
        member = await bot.get_chat_member(chat_id=fwd.id, user_id=me.id)
        if member.status not in ("administrator", "creator"):
            await message.answer(T.addsp_bot_not_admin, reply_markup=kb_add_cancel())
            return
    except TelegramAPIError:
        await message.answer(T.addsp_bot_not_admin, reply_markup=kb_add_cancel())
        return
    await state.update_data(chat_id=fwd.id, suggested_title=fwd.title or "")
    await state.set_state(AddSponsorStates.waiting_title)
    hint = f"\n\nПодсказка: <b>{fwd.title}</b>" if fwd.title else ""
    await message.answer(T.addsp_step4_private + hint, reply_markup=kb_add_cancel())


@router.message(AddSponsorStates.waiting_title)
async def msg_title(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if message.text is None or not message.text.strip():
        await message.answer(T.addsp_title_invalid, reply_markup=kb_add_cancel())
        return
    title = message.text.strip()[:255]
    data = await state.get_data()
    kind = SponsorKind(data["kind"])
    sponsor = await SponsorRepo(session).create(
        kind=kind,
        title=title,
        chat_id=data.get("chat_id"),
        username=data.get("username"),
        invite_link=data.get("invite_link"),
        is_required=True,
        is_active=True,
    )
    await state.clear()
    await message.answer(
        T.addsp_created.format(title=sponsor.title),
        reply_markup=kb_admin_root(),
    )


# ---------- edit reward / subs_limit for OPTIONAL sponsors ----------

@router.callback_query(F.data.startswith("adm:sp:edit_rw:"))
async def cb_edit_reward(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    sid = _parse_id(callback.data)
    if sid is None:
        await callback.answer()
        return
    s = await SponsorRepo(session).get(sid)
    if s is None:
        await callback.answer(T.admin_sponsor_deleted, show_alert=True)
        return
    await state.set_state(EditSponsorStates.waiting_reward)
    await state.update_data(sponsor_id=sid)
    if callback.message is not None:
        with suppress(Exception):
            await callback.message.edit_text(
                T.editsp_reward_prompt.format(title=s.title, current=s.reward),
                reply_markup=kb_add_cancel(),
            )
    await callback.answer()


@router.message(EditSponsorStates.waiting_reward)
async def msg_edit_reward(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if message.text is None:
        await message.answer(T.editsp_reward_invalid, reply_markup=kb_add_cancel())
        return
    raw = message.text.strip().replace(",", ".")
    try:
        reward = float(raw)
    except ValueError:
        await message.answer(T.editsp_reward_invalid, reply_markup=kb_add_cancel())
        return
    if reward < 0 or reward > 1_000_000:
        await message.answer(T.editsp_reward_invalid, reply_markup=kb_add_cancel())
        return
    reward = round(reward, 2)
    data = await state.get_data()
    sid = int(data.get("sponsor_id", 0))
    repo = SponsorRepo(session)
    if sid <= 0 or (await repo.get(sid)) is None:
        await state.clear()
        await message.answer(T.admin_sponsor_deleted)
        return
    await repo.set_reward(sid, reward)
    s = await repo.get(sid)
    await state.clear()
    if s is not None:
        await message.answer(
            T.editsp_reward_saved.format(title=s.title, reward=reward),
            reply_markup=kb_sponsor_card(s),
        )
        await message.answer(_format_card(s), reply_markup=kb_sponsor_card(s))


@router.callback_query(F.data.startswith("adm:sp:edit_lm:"))
async def cb_edit_limit(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    sid = _parse_id(callback.data)
    if sid is None:
        await callback.answer()
        return
    s = await SponsorRepo(session).get(sid)
    if s is None:
        await callback.answer(T.admin_sponsor_deleted, show_alert=True)
        return
    await state.set_state(EditSponsorStates.waiting_subs_limit)
    await state.update_data(sponsor_id=sid)
    if callback.message is not None:
        with suppress(Exception):
            await callback.message.edit_text(
                T.editsp_limit_prompt.format(title=s.title, current=s.subs_limit),
                reply_markup=kb_add_cancel(),
            )
    await callback.answer()


@router.message(EditSponsorStates.waiting_subs_limit)
async def msg_edit_limit(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if message.text is None or not message.text.strip().isdigit():
        await message.answer(T.editsp_limit_invalid, reply_markup=kb_add_cancel())
        return
    limit = int(message.text.strip())
    if limit > 1_000_000_000:
        await message.answer(T.editsp_limit_invalid, reply_markup=kb_add_cancel())
        return
    data = await state.get_data()
    sid = int(data.get("sponsor_id", 0))
    repo = SponsorRepo(session)
    if sid <= 0 or (await repo.get(sid)) is None:
        await state.clear()
        await message.answer(T.admin_sponsor_deleted)
        return
    await repo.set_subs_limit(sid, limit)
    s = await repo.get(sid)
    await state.clear()
    if s is not None:
        await message.answer(
            T.editsp_limit_saved.format(title=s.title, limit=limit),
            reply_markup=kb_sponsor_card(s),
        )
        await message.answer(_format_card(s), reply_markup=kb_sponsor_card(s))


# ---------- helpers ----------

def _parse_id(data: str | None) -> int | None:
    if data is None:
        return None
    parts = data.split(":")
    if not parts[-1].isdigit():
        return None
    return int(parts[-1])

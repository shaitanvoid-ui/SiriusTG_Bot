"""Админка: раздел «Поддержка» (Этап 11).

Список тикетов по статусам, карточка с тредом, ответ юзеру в DM, закрытие.
"""

from __future__ import annotations

from contextlib import suppress

from aiogram import Bot, F, Router, html
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.filters.admin import IsAdmin
from bot.handlers.admin._common import user_label
from bot.keyboards.support import (
    admin_status_label,
    kb_admin_sup_card,
    kb_admin_sup_list,
    kb_open_ticket_dm,
)
from bot.states.admin import SupportAdminStates
from db.models import SupportTicket, TicketStatus
from db.repositories.support import TicketRepo
from db.repositories.user import UserRepo
from locales.ru import T
from services.support import SupportService, render_thread
from utils.tz import fmt_dt

router = Router(name="admin_support")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


async def _labels_for(
    session: AsyncSession, tickets: list[SupportTicket]
) -> dict[int, str]:
    user_repo = UserRepo(session)
    labels: dict[int, str] = {}
    for t in tickets:
        if t.user_id not in labels:
            labels[t.user_id] = user_label(await user_repo.get_by_id(t.user_id))
    return labels


async def _render_root(message: Message, session: AsyncSession) -> None:
    repo = TicketRepo(session)
    counts = await repo.counts_by_status()
    tickets = await repo.list_open(limit=20)
    text = T.admin_sup_root.format(
        new=counts[TicketStatus.NEW.value],
        in_progress=counts[TicketStatus.IN_PROGRESS.value],
        awaiting=counts[TicketStatus.AWAITING.value],
        closed=counts[TicketStatus.CLOSED.value],
        hint=T.admin_sup_root_hint if tickets else T.admin_sup_root_empty,
    )
    with suppress(TelegramBadRequest):
        await message.edit_text(
            text,
            reply_markup=kb_admin_sup_list(tickets, await _labels_for(session, tickets)),
        )


@router.callback_query(F.data == "adm:sup")
async def cb_root(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    if callback.message is None:
        await callback.answer()
        return
    await state.clear()
    await _render_root(callback.message, session)
    await callback.answer()


@router.callback_query(F.data == "adm:sup:arch")
async def cb_archive(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.message is None:
        await callback.answer()
        return
    tickets = await TicketRepo(session).list_closed(limit=20)
    text = T.admin_sup_archive_caption.format(
        hint=T.admin_sup_root_hint if tickets else T.admin_sup_archive_empty
    )
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            text,
            reply_markup=kb_admin_sup_list(
                tickets, await _labels_for(session, tickets), archive=True
            ),
        )
    await callback.answer()


# ---------- карточка ----------

async def _card_view(session: AsyncSession, ticket: SupportTicket):
    """(text, keyboard) карточки — для edit и для отправки новым сообщением."""
    user = await UserRepo(session).get_by_id(ticket.user_id)
    messages = await TicketRepo(session).list_messages(ticket.id, limit=8)
    text = T.admin_sup_card.format(
        id=ticket.id,
        user_info=html.quote(user_label(user)),
        status=admin_status_label(ticket.status),
        created=fmt_dt(ticket.created_at),
        thread=render_thread(messages),
    )
    from_archive = ticket.status == TicketStatus.CLOSED.value
    return text, kb_admin_sup_card(ticket, from_archive=from_archive)


async def _render_card(
    message: Message, session: AsyncSession, ticket: SupportTicket
) -> None:
    text, kb = await _card_view(session, ticket)
    with suppress(TelegramBadRequest):
        await message.edit_text(text, reply_markup=kb)


async def _ticket_from_cb(
    callback: CallbackQuery, session: AsyncSession
) -> SupportTicket | None:
    ticket_id = int((callback.data or "0").rsplit(":", 1)[-1])
    return await TicketRepo(session).get_by_id(ticket_id)


@router.callback_query(F.data.startswith("adm:sup:open:"))
async def cb_open_ticket(callback: CallbackQuery, session: AsyncSession) -> None:
    ticket = await _ticket_from_cb(callback, session)
    if ticket is None or callback.message is None:
        await callback.answer(T.admin_sup_not_found_alert, show_alert=True)
        return
    await _render_card(callback.message, session, ticket)
    await callback.answer()


# ---------- ответ ----------

@router.callback_query(F.data.startswith("adm:sup:reply:"))
async def cb_reply_prompt(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    ticket = await _ticket_from_cb(callback, session)
    if ticket is None or callback.message is None:
        await callback.answer(T.admin_sup_not_found_alert, show_alert=True)
        return
    if ticket.status == TicketStatus.CLOSED.value:
        await callback.answer(T.admin_sup_already_closed_alert, show_alert=True)
        return
    await state.set_state(SupportAdminStates.waiting_reply)
    await state.update_data(ticket_id=ticket.id)
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(T.admin_sup_reply_prompt.format(id=ticket.id))
    await callback.answer()


@router.message(SupportAdminStates.waiting_reply, F.text)
async def msg_reply(
    message: Message, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    data = await state.get_data()
    await state.clear()
    repo = TicketRepo(session)
    ticket = await repo.get_by_id(int(data.get("ticket_id", 0)))
    if ticket is None:
        await message.answer(T.admin_sup_not_found_alert)
        return
    text = (message.text or "").strip()
    added = await SupportService(session).admin_reply(ticket, text)
    if added is None:
        await message.answer(T.admin_sup_already_closed_alert)
        return

    # DM юзеру — ответы поддержки не гасятся преференциями
    user = await UserRepo(session).get_by_id(ticket.user_id)
    if user is not None:
        with suppress(TelegramAPIError):
            await bot.send_message(
                user.tg_id,
                T.notify_support_reply.format(id=ticket.id, text=html.quote(text[:500])),
                reply_markup=kb_open_ticket_dm(ticket.id),
            )
    await message.answer(T.admin_sup_reply_sent)
    text, kb = await _card_view(session, ticket)
    await message.answer(text, reply_markup=kb)


# ---------- закрытие ----------

@router.callback_query(F.data.startswith("adm:sup:close:"))
async def cb_close(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    ticket = await _ticket_from_cb(callback, session)
    if ticket is None or callback.message is None:
        await callback.answer(T.admin_sup_not_found_alert, show_alert=True)
        return
    closed = await SupportService(session).close(ticket, by="admin")
    if not closed:
        await callback.answer(T.admin_sup_already_closed_alert, show_alert=True)
        return
    user = await UserRepo(session).get_by_id(ticket.user_id)
    if user is not None:
        with suppress(TelegramAPIError):
            await bot.send_message(user.tg_id, T.notify_support_closed.format(id=ticket.id))
    await _render_card(callback.message, session, ticket)
    await callback.answer(T.admin_sup_closed_alert)

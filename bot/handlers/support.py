"""Поддержка, юзер-сайд (Этап 11): FAQ → новый вопрос → мои обращения."""

from __future__ import annotations

from contextlib import suppress

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.support import (
    kb_faq_answer,
    kb_faq_list,
    kb_my_tickets,
    kb_support_cancel,
    kb_support_created,
    kb_support_home,
    kb_ticket_card,
    user_status_label,
)
from bot.states.support import SupportStates
from core.config import settings as app_settings
from db.models import SupportTicket, TicketStatus, User
from db.repositories.support import TicketRepo
from locales.ru import T
from services.settings import SettingsService
from services.support import CreateStatus, SupportService, render_thread
from utils.tz import fmt_dt

router = Router(name="support")


# ---------- хаб ----------

@router.callback_query(F.data == "sup:open")
async def cb_support_home(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    if callback.message is None:
        await callback.answer()
        return
    if not await SettingsService(session).get_bool("support.enabled", True):
        await callback.answer(T.support_disabled_alert, show_alert=True)
        return
    await state.clear()
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(T.support_home, reply_markup=kb_support_home())
    await callback.answer()


@router.callback_query(F.data == "sup:cancel")
async def cb_support_cancel(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    await state.clear()
    if callback.message is not None:
        with suppress(TelegramBadRequest):
            await callback.message.edit_text(T.support_home, reply_markup=kb_support_home())
    await callback.answer()


# ---------- FAQ ----------

async def _faq_items(session: AsyncSession) -> list[dict]:
    items = await SettingsService(session).get_list("support.faq", [])
    return [i for i in items if isinstance(i, dict) and i.get("q") and i.get("a")]


@router.callback_query(F.data == "sup:faq")
async def cb_faq_home(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.message is None:
        await callback.answer()
        return
    items = await _faq_items(session)
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            T.support_faq_home,
            reply_markup=kb_faq_list([str(i["q"]) for i in items]),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("sup:faq:"))
async def cb_faq_answer(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.message is None:
        await callback.answer()
        return
    idx = int(callback.data.rsplit(":", 1)[-1])
    items = await _faq_items(session)
    if idx >= len(items):
        await callback.answer()
        return
    item = items[idx]
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            T.support_faq_answer.format(question=item["q"], answer=item["a"]),
            reply_markup=kb_faq_answer(),
        )
    await callback.answer()


# ---------- новый вопрос ----------

@router.callback_query(F.data == "sup:new")
async def cb_new_ticket(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    if callback.message is None:
        await callback.answer()
        return
    s = SettingsService(session)
    if not await s.get_bool("support.enabled", True):
        await callback.answer(T.support_disabled_alert, show_alert=True)
        return
    min_len = await s.get_int("support.min_text_length", 10)
    max_len = await s.get_int("support.max_text_length", 1500)
    await state.set_state(SupportStates.waiting_text)
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            T.support_new_prompt.format(min_len=min_len, max_len=max_len),
            reply_markup=kb_support_cancel(),
        )
    await callback.answer()


@router.message(SupportStates.waiting_text, F.text)
async def msg_new_ticket(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    db_user: User,
) -> None:
    svc = SupportService(session)
    result = await svc.create_ticket(db_user, message.text or "")

    if result.status is CreateStatus.TOO_SHORT:
        await message.answer(T.support_text_too_short.format(min_len=result.min_len))
        return
    if result.status is CreateStatus.TOO_LONG:
        await message.answer(T.support_text_too_long.format(max_len=result.max_len))
        return
    await state.clear()
    if result.status is CreateStatus.TOO_MANY:
        await message.answer(T.support_too_many_alert, reply_markup=kb_support_home())
        return
    if result.status is CreateStatus.DISABLED or result.ticket is None:
        await message.answer(T.support_disabled_alert, reply_markup=kb_support_home())
        return

    ticket = result.ticket
    await message.answer(
        T.support_created.format(id=ticket.id), reply_markup=kb_support_created()
    )
    if app_settings.log_channel_id:
        with suppress(TelegramAPIError):
            await bot.send_message(
                app_settings.log_channel_id,
                T.log_support_new_ticket.format(
                    id=ticket.id, tg_id=db_user.tg_id, subject=ticket.subject
                ),
            )


# ---------- мои обращения ----------

@router.callback_query(F.data == "sup:my")
async def cb_my_tickets(
    callback: CallbackQuery, session: AsyncSession, db_user: User
) -> None:
    if callback.message is None:
        await callback.answer()
        return
    tickets = await TicketRepo(session).list_for_user(db_user.id)
    text = T.support_my_list if tickets else T.support_my_empty
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(text, reply_markup=kb_my_tickets(tickets))
    await callback.answer()


async def _own_ticket(
    callback: CallbackQuery, session: AsyncSession, db_user: User
) -> SupportTicket | None:
    ticket_id = int((callback.data or "0").rsplit(":", 1)[-1])
    ticket = await TicketRepo(session).get_by_id(ticket_id)
    if ticket is None or ticket.user_id != db_user.id:
        return None
    return ticket


async def _render_ticket_card(
    message: Message, session: AsyncSession, ticket: SupportTicket
) -> None:
    messages = await TicketRepo(session).list_messages(ticket.id, limit=8)
    text = T.support_ticket_card.format(
        id=ticket.id,
        status=user_status_label(ticket.status),
        created=fmt_dt(ticket.created_at),
        thread=render_thread(messages),
    )
    with suppress(TelegramBadRequest):
        await message.edit_text(text, reply_markup=kb_ticket_card(ticket))


@router.callback_query(F.data.startswith("sup:t:reply:"))
async def cb_ticket_reply(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, db_user: User
) -> None:
    ticket = await _own_ticket(callback, session, db_user)
    if ticket is None or callback.message is None:
        await callback.answer()
        return
    if ticket.status == TicketStatus.CLOSED.value:
        await callback.answer(T.support_ticket_closed_alert, show_alert=True)
        return
    await state.set_state(SupportStates.waiting_reply)
    await state.update_data(ticket_id=ticket.id)
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            T.support_reply_prompt.format(id=ticket.id),
            reply_markup=kb_support_cancel(),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("sup:t:close:"))
async def cb_ticket_close(
    callback: CallbackQuery, session: AsyncSession, db_user: User
) -> None:
    ticket = await _own_ticket(callback, session, db_user)
    if ticket is None or callback.message is None:
        await callback.answer()
        return
    closed = await SupportService(session).close(ticket, by="user")
    await _render_ticket_card(callback.message, session, ticket)
    await callback.answer(
        T.support_closed_alert if closed else T.support_ticket_closed_alert
    )


@router.callback_query(F.data.startswith("sup:t:"))
async def cb_ticket_card(
    callback: CallbackQuery, session: AsyncSession, db_user: User
) -> None:
    ticket = await _own_ticket(callback, session, db_user)
    if ticket is None or callback.message is None:
        await callback.answer()
        return
    await _render_ticket_card(callback.message, session, ticket)
    await callback.answer()


@router.message(SupportStates.waiting_reply, F.text)
async def msg_ticket_reply(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    db_user: User,
) -> None:
    data = await state.get_data()
    ticket = await TicketRepo(session).get_by_id(int(data.get("ticket_id", 0)))
    await state.clear()
    if ticket is None or ticket.user_id != db_user.id:
        await message.answer(T.support_my_empty, reply_markup=kb_support_home())
        return
    added = await SupportService(session).user_reply(db_user, ticket, message.text or "")
    if added is None:
        await message.answer(T.support_ticket_closed_alert, reply_markup=kb_support_home())
        return

    messages = await TicketRepo(session).list_messages(ticket.id, limit=8)
    await message.answer(
        T.support_ticket_card.format(
            id=ticket.id,
            status=user_status_label(ticket.status),
            created=fmt_dt(ticket.created_at),
            thread=render_thread(messages),
        ),
        reply_markup=kb_ticket_card(ticket),
    )
    if app_settings.log_channel_id:
        with suppress(TelegramAPIError):
            await bot.send_message(
                app_settings.log_channel_id,
                T.log_support_user_reply.format(tg_id=db_user.tg_id, id=ticket.id),
            )

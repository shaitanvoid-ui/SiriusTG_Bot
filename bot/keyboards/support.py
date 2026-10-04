"""Клавиатуры поддержки (Этап 11): юзер-сайд и админка."""

from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from utils.keyboards import SiriusKeyboardBuilder as InlineKeyboardBuilder

from db.models import SupportTicket, TicketStatus
from locales.ru import T
from utils.ui import button_text


# ---------- юзер ----------

def kb_support_home() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=T.btn_support_new, callback_data="sup:new", style="primary")
    b.button(text=T.btn_support_faq, callback_data="sup:faq")
    b.button(text=T.btn_support_my, callback_data="sup:my")
    b.footer(text=T.btn_back_help, callback_data="sec:help")
    b.adjust(1, 2, 2)
    return b.as_markup()


def kb_faq_list(questions: list[str]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for idx, question in enumerate(questions):
        b.button(text=button_text(f"❔ {question}"), callback_data=f"sup:faq:{idx}")
    b.button(text=T.btn_support_new, callback_data="sup:new")
    b.footer(text=T.btn_support_back, callback_data="sup:open")
    b.adjust(*([1] * (len(questions) + 1)), 2)
    return b.as_markup()


def kb_faq_answer() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=T.btn_support_new, callback_data="sup:new")
    b.footer(text=T.btn_support_faq_back, callback_data="sup:faq")
    b.adjust(1, 2)
    return b.as_markup()


def kb_support_cancel() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=T.btn_cancel, callback_data="sup:cancel")
    return b.as_markup()


def kb_support_reply_cancel(ticket_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=T.btn_back, callback_data=f"sup:t:reply_cancel:{ticket_id}")
    return b.as_markup()


def kb_support_close_confirm(ticket_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(
        text=T.btn_support_close_confirm,
        callback_data=f"sup:t:close_yes:{ticket_id}",
    )
    b.button(
        text=T.btn_support_close_cancel,
        callback_data=f"sup:t:{ticket_id}",
    )
    b.adjust(1, 1)
    return b.as_markup()


def kb_support_created() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.footer(text=T.btn_support_my, callback_data="sup:my")
    b.adjust(2)
    return b.as_markup()


def user_status_label(status: str) -> str:
    return {
        TicketStatus.NEW.value: T.support_status_new,
        TicketStatus.IN_PROGRESS.value: T.support_status_in_progress,
        TicketStatus.AWAITING.value: T.support_status_awaiting,
        TicketStatus.CLOSED.value: T.support_status_closed,
    }.get(status, status)


def _status_dot(status: str) -> str:
    return {
        TicketStatus.NEW.value: "🕓",
        TicketStatus.IN_PROGRESS.value: "🕓",
        TicketStatus.AWAITING.value: "💬",
        TicketStatus.CLOSED.value: "✔️",
    }.get(status, "•")


def kb_my_tickets(tickets: list[SupportTicket]) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for t in tickets:
        subject = button_text(t.subject, limit=32)
        b.button(
            text=T.support_ticket_row.format(
                status=_status_dot(t.status), id=t.id, subject=subject
            ),
            callback_data=f"sup:t:{t.id}",
        )
    b.footer(text=T.btn_support_back, callback_data="sup:open")
    b.adjust(*([1] * len(tickets)), 2)
    return b.as_markup()


def kb_ticket_card(ticket: SupportTicket) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    rows: list[int] = []
    if ticket.status != TicketStatus.CLOSED.value:
        b.button(text=T.btn_support_reply, callback_data=f"sup:t:reply:{ticket.id}")
        b.button(text=T.btn_support_close, callback_data=f"sup:t:close:{ticket.id}")
        rows.extend([1, 1])
    b.footer(text=T.btn_support_to_my, callback_data="sup:my")
    rows.append(2)
    b.adjust(*rows)
    return b.as_markup()


def kb_open_ticket_dm(ticket_id: int) -> InlineKeyboardMarkup:
    """Кнопка под DM-уведомлением об ответе поддержки."""
    b = InlineKeyboardBuilder()
    b.button(text=T.btn_support_open_ticket, callback_data=f"sup:t:{ticket_id}")
    return b.as_markup()


# ---------- админка ----------

def admin_status_label(status: str) -> str:
    return {
        TicketStatus.NEW.value: T.admin_sup_status_new,
        TicketStatus.IN_PROGRESS.value: T.admin_sup_status_in_progress,
        TicketStatus.AWAITING.value: T.admin_sup_status_awaiting,
        TicketStatus.CLOSED.value: T.admin_sup_status_closed,
    }.get(status, status)


def _admin_status_dot(status: str) -> str:
    return {
        TicketStatus.NEW.value: "🔴",
        TicketStatus.IN_PROGRESS.value: "🟠",
        TicketStatus.AWAITING.value: "🟢",
        TicketStatus.CLOSED.value: "✔️",
    }.get(status, "•")


def kb_admin_sup_list(
    tickets: list[SupportTicket],
    user_labels: dict[int, str],
    *,
    archive: bool = False,
) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for t in tickets:
        subject = button_text(t.subject, limit=24)
        b.button(
            text=T.admin_sup_row.format(
                status=_admin_status_dot(t.status),
                id=t.id,
                user=button_text(user_labels.get(t.user_id, "?"), limit=16),
                subject=subject,
            ),
            callback_data=f"adm:sup:open:{t.id}",
        )
    if archive:
        b.button(text=T.btn_admin_sup_open, callback_data="adm:sup")
    else:
        b.button(text=T.btn_admin_sup_archive, callback_data="adm:sup:arch")
    b.footer(text=T.btn_back_admin, callback_data="adm:root")
    b.adjust(*([1] * len(tickets)), 1, 1)
    return b.as_markup()


def kb_admin_sup_card(ticket: SupportTicket, *, from_archive: bool = False) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    rows: list[int] = []
    if ticket.status != TicketStatus.CLOSED.value:
        b.button(text=T.btn_admin_sup_reply, callback_data=f"adm:sup:reply:{ticket.id}")
        b.button(text=T.btn_admin_sup_close, callback_data=f"adm:sup:close:{ticket.id}")
        rows.extend([1, 1])
    back_cb = "adm:sup:arch" if from_archive else "adm:sup"
    b.footer(text="‹ К списку", callback_data=back_cb)
    rows.append(2)
    b.adjust(*rows)
    return b.as_markup()


def kb_admin_sup_reply_cancel(ticket_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=T.btn_back, callback_data=f"adm:sup:reply_cancel:{ticket_id}")
    return b.as_markup()


def kb_admin_sup_close_confirm(ticket_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(
        text=T.btn_support_close_confirm,
        callback_data=f"adm:sup:close_yes:{ticket_id}",
    )
    b.button(
        text=T.btn_support_close_cancel,
        callback_data=f"adm:sup:open:{ticket_id}",
    )
    b.adjust(1, 1)
    return b.as_markup()

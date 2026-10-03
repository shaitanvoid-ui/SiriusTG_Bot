"""Бизнес-логика поддержки (Этап 11).

Жизненный цикл тикета:
  NEW (юзер создал) → AWAITING (админ ответил) → IN_PROGRESS (юзер дописал)
    → ... → CLOSED (юзер/админ/автозакрытие).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum

from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.base import utcnow
from db.models import SupportMessage, SupportTicket, TicketAuthor, TicketStatus, User
from db.repositories.action_log import ActionLogRepo
from db.repositories.support import TicketRepo
from services.settings import SettingsService

log = get_logger(__name__)

SUBJECT_MAX_LEN = 60
THREAD_MSG_MAX_CHARS = 300
THREAD_VISIBLE_MESSAGES = 8
THREAD_RENDER_MAX_CHARS = 2_400


def render_thread(messages: list[SupportMessage]) -> str:
    """Переписка тикета для карточки (юзерской и админской)."""
    from aiogram import html

    from locales.ru import T

    selected: list[str] = []
    for msg in reversed(messages):
        text = msg.text.strip()
        if len(text) > THREAD_MSG_MAX_CHARS:
            text = text[: THREAD_MSG_MAX_CHARS - 1] + "…"
        template = (
            T.support_thread_admin_line
            if msg.author == TicketAuthor.ADMIN.value
            else T.support_thread_user_line
        )
        line = template.format(text=html.quote(text))
        extra = len(line) + (2 if selected else 0)
        if selected and (
            len(selected) >= THREAD_VISIBLE_MESSAGES
            or sum(map(len, selected)) + 2 * (len(selected) - 1) + extra
            > THREAD_RENDER_MAX_CHARS
        ):
            break
        selected.append(line)
    selected.reverse()
    lines = selected
    if len(selected) < len(messages):
        lines.insert(0, T.support_thread_older_omitted)
    return "\n\n".join(lines)


class CreateStatus(StrEnum):
    OK = "ok"
    DISABLED = "disabled"
    TOO_MANY = "too_many"
    TOO_SHORT = "too_short"
    TOO_LONG = "too_long"


@dataclass(frozen=True)
class CreateResult:
    status: CreateStatus
    ticket: SupportTicket | None = None
    min_len: int = 0
    max_len: int = 0


def make_subject(text: str) -> str:
    """Тема тикета — первая строка обращения, обрезанная до лимита."""
    first_line = text.strip().splitlines()[0].strip()
    if len(first_line) <= SUBJECT_MAX_LEN:
        return first_line
    return first_line[: SUBJECT_MAX_LEN - 1] + "…"


class SupportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = TicketRepo(session)
        self.settings = SettingsService(session)

    # ---------- создание ----------

    async def create_ticket(self, user: User, text: str) -> CreateResult:
        if not await self.settings.get_bool("support.enabled", True):
            return CreateResult(status=CreateStatus.DISABLED)

        min_len = await self.settings.get_int("support.min_text_length", 10)
        max_len = await self.settings.get_int("support.max_text_length", 1500)
        text = text.strip()
        if len(text) < min_len:
            return CreateResult(status=CreateStatus.TOO_SHORT, min_len=min_len, max_len=max_len)
        if len(text) > max_len:
            return CreateResult(status=CreateStatus.TOO_LONG, min_len=min_len, max_len=max_len)

        max_per_hour = await self.settings.get_int("support.max_tickets_per_hour", 3)
        recent = await self.repo.count_recent_for_user(
            user.id, utcnow() - timedelta(hours=1)
        )
        if recent >= max_per_hour:
            return CreateResult(status=CreateStatus.TOO_MANY)

        ticket = await self.repo.create(user.id, make_subject(text), text)
        await self.repo.add_message(ticket, TicketAuthor.USER, text)
        await ActionLogRepo(self.session).log(
            user_tg_id=user.tg_id,
            action="support_ticket_created",
            payload={"ticket_id": ticket.id},
        )
        log.info("support_ticket_created", ticket_id=ticket.id, user_tg_id=user.tg_id)
        return CreateResult(status=CreateStatus.OK, ticket=ticket)

    # ---------- переписка ----------

    async def user_reply(
        self, user: User, ticket: SupportTicket, text: str
    ) -> SupportMessage | None:
        """Реплика юзера в свой открытый тикет. None — тикет закрыт/чужой."""
        if ticket.user_id != user.id or ticket.status == TicketStatus.CLOSED.value:
            return None
        msg = await self.repo.add_message(ticket, TicketAuthor.USER, text.strip())
        await self.repo.set_status(ticket, TicketStatus.IN_PROGRESS)
        return msg

    async def admin_reply(self, ticket: SupportTicket, text: str) -> SupportMessage | None:
        if ticket.status == TicketStatus.CLOSED.value:
            return None
        msg = await self.repo.add_message(ticket, TicketAuthor.ADMIN, text.strip())
        await self.repo.set_status(ticket, TicketStatus.AWAITING)
        return msg

    # ---------- закрытие ----------

    async def close(self, ticket: SupportTicket, *, by: str) -> bool:
        """by ∈ {'user', 'admin', 'auto'} — для ActionLog."""
        if ticket.status == TicketStatus.CLOSED.value:
            return False
        await self.repo.set_status(ticket, TicketStatus.CLOSED)
        await ActionLogRepo(self.session).log(
            user_tg_id=None,
            action="support_ticket_closed",
            payload={"ticket_id": ticket.id, "by": by},
        )
        return True

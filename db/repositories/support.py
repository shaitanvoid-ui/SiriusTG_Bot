"""Support ticket repo (Этап 8: конвертация отзыва; Этап 11: полный флоу)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select

from db.base import utcnow
from db.models import SupportMessage, SupportTicket, TicketAuthor, TicketStatus
from db.repositories.base import BaseRepo


class TicketRepo(BaseRepo):
    async def create(
        self,
        user_id: int,
        subject: str,
        text: str,
        review_id: int | None = None,
    ) -> SupportTicket:
        ticket = SupportTicket(
            user_id=user_id,
            subject=subject,
            text=text,
            review_id=review_id,
            status=TicketStatus.NEW.value,
        )
        self.session.add(ticket)
        await self.session.flush()
        return ticket

    async def get_by_id(self, ticket_id: int) -> SupportTicket | None:
        res = await self.session.execute(
            select(SupportTicket).where(SupportTicket.id == ticket_id)
        )
        return res.scalar_one_or_none()

    async def list_for_user(self, user_id: int, limit: int = 10) -> list[SupportTicket]:
        res = await self.session.execute(
            select(SupportTicket)
            .where(SupportTicket.user_id == user_id)
            .order_by(SupportTicket.updated_at.desc(), SupportTicket.id.desc())
            .limit(limit)
        )
        return list(res.scalars().all())

    async def list_open(self, limit: int = 20) -> list[SupportTicket]:
        """Открытые тикеты для админ-списка: сперва ждущие админа, потом остальные."""
        res = await self.session.execute(
            select(SupportTicket)
            .where(SupportTicket.status != TicketStatus.CLOSED.value)
            .order_by(
                # new/in_progress (ждут админа) выше awaiting
                (SupportTicket.status == TicketStatus.AWAITING.value).asc(),
                SupportTicket.updated_at.asc(),
            )
            .limit(limit)
        )
        return list(res.scalars().all())

    async def list_closed(self, limit: int = 20) -> list[SupportTicket]:
        res = await self.session.execute(
            select(SupportTicket)
            .where(SupportTicket.status == TicketStatus.CLOSED.value)
            .order_by(SupportTicket.updated_at.desc(), SupportTicket.id.desc())
            .limit(limit)
        )
        return list(res.scalars().all())

    async def counts_by_status(self) -> dict[str, int]:
        res = await self.session.execute(
            select(SupportTicket.status, func.count(SupportTicket.id))
            .group_by(SupportTicket.status)
        )
        counts = {status.value: 0 for status in TicketStatus}
        for status, count in res.all():
            counts[str(status)] = int(count)
        return counts

    async def count_recent_for_user(self, user_id: int, since: datetime) -> int:
        """Сколько тикетов юзер создал с момента since — для антиспама."""
        res = await self.session.execute(
            select(func.count(SupportTicket.id)).where(
                SupportTicket.user_id == user_id,
                SupportTicket.created_at >= since,
            )
        )
        return int(res.scalar_one() or 0)

    async def set_status(self, ticket: SupportTicket, status: TicketStatus) -> None:
        ticket.status = status.value
        ticket.updated_at = utcnow()
        if status is TicketStatus.CLOSED:
            ticket.closed_at = utcnow()

    async def list_autoclose_candidates(
        self, cutoff: datetime, limit: int = 100
    ) -> list[SupportTicket]:
        """Тикеты, где админ ответил, а юзер молчит дольше cutoff."""
        res = await self.session.execute(
            select(SupportTicket)
            .where(
                SupportTicket.status == TicketStatus.AWAITING.value,
                SupportTicket.updated_at < cutoff,
            )
            .limit(limit)
        )
        return list(res.scalars().all())

    # ---------- тред ----------

    async def add_message(
        self, ticket: SupportTicket, author: TicketAuthor, text: str
    ) -> SupportMessage:
        msg = SupportMessage(ticket_id=ticket.id, author=author.value, text=text)
        self.session.add(msg)
        # касание тикета, чтобы автозакрытие отсчитывалось от последней реплики
        ticket.updated_at = utcnow()
        await self.session.flush()
        return msg

    async def list_messages(self, ticket_id: int, limit: int = 20) -> list[SupportMessage]:
        """Последние limit сообщений треда в хронологическом порядке."""
        res = await self.session.execute(
            select(SupportMessage)
            .where(SupportMessage.ticket_id == ticket_id)
            .order_by(SupportMessage.created_at.desc(), SupportMessage.id.desc())
            .limit(limit)
        )
        return list(reversed(res.scalars().all()))

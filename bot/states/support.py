from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class SupportStates(StatesGroup):
    """Поддержка, юзер-сторона (Этап 11)."""

    waiting_text = State()   # текст нового обращения
    waiting_reply = State()  # реплика в существующий тикет (ticket_id в data)

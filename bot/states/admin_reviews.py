"""FSM для модерации отзывов."""
from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class ReviewModStates(StatesGroup):
    waiting_note = State()

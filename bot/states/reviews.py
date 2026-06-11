"""FSM-состояния для отзывов (Этап 8)."""
from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class ReviewStates(StatesGroup):
    rating = State()
    text = State()
    anonymity = State()
    confirm = State()
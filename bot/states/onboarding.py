from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class OnboardingStates(StatesGroup):
    awaiting_terms = State()
    awaiting_captcha = State()
    awaiting_subs = State()

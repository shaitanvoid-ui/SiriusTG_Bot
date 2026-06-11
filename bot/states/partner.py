"""FSM-состояния партнёрской панели (Этап 10)."""
from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class PartnerLinkStates(StatesGroup):
    waiting_title = State()        # название новой UTM-ссылки


class PartnerSponsorStates(StatesGroup):
    waiting_channel = State()      # @username канала партнёра


class PartnerPayoutStates(StatesGroup):
    waiting_requisites = State()   # реквизиты (карта/кошелёк)

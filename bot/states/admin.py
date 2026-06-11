from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class AddSponsorStates(StatesGroup):
    waiting_kind = State()
    waiting_chat = State()              # public: forward или @username
    waiting_invite = State()            # private: invite-link
    waiting_private_forward = State()   # private: forward поста для chat_id
    waiting_title = State()


class AddPromoStates(StatesGroup):
    waiting_code = State()
    waiting_reward = State()
    waiting_max_activations = State()
    waiting_expires_days = State()
    waiting_honeypot = State()


class EditSponsorStates(StatesGroup):
    waiting_reward = State()      # ввод новой награды (float)
    waiting_subs_limit = State()  # ввод нового лимита (int)


class InstructionStates(StatesGroup):
    """Редактор инструкции (Этап 8/9)."""
    waiting_new_title = State()
    waiting_new_body = State()
    waiting_edit_title = State()
    waiting_edit_body = State()


class SetChannelStates(StatesGroup):
    """Установка канала проекта (Этап 8)."""
    waiting_channel = State()     # @username или forward поста


class UserAdminStates(StatesGroup):
    """Раздел «Юзеры» (Этап 9)."""
    waiting_query = State()       # tg_id или @username
    waiting_balance_delta = State()  # ввод суммы ±⭐


class EcoEditStates(StatesGroup):
    """Редактор экономики (Этап 9)."""
    waiting_value = State()


class BroadcastStates(StatesGroup):
    """Рассылка (Этап 9)."""
    waiting_text = State()
    confirming = State()


class StopWordStates(StatesGroup):
    """Стоп-слова отзывов (Этап 8/9)."""
    waiting_add = State()
    waiting_remove = State()


class PartnerAdminStates(StatesGroup):
    """Раздел «Партнёры» (Этап 10)."""
    waiting_user_query = State()   # tg_id или @username нового партнёра
    waiting_cpa = State()          # персональная ставка CPA (⭐)
    waiting_percent = State()      # персональный % со спонсоров


class SupportAdminStates(StatesGroup):
    """Раздел «Поддержка» (Этап 11)."""
    waiting_reply = State()        # текст ответа админа (ticket_id в data)

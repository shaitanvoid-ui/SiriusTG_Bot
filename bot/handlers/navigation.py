"""Every stale button receives an answer; idle chat input offers navigation."""

from aiogram import Router
from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery, Message
from utils.ui import kb_back_to_menu
from locales.ru import T


router = Router(name="navigation_fallback")


@router.callback_query()
async def stale_callback(callback: CallbackQuery) -> None:
    await callback.answer(T.stale_screen_alert, show_alert=True)


@router.message(StateFilter(None))
async def idle_message(message: Message) -> None:
    await message.answer(T.navigation_hint, reply_markup=kb_back_to_menu())

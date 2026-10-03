"""Хендлеры подразделов главного меню: Заработать, Помощь."""

from __future__ import annotations

from utils.telegram import ignore_unchanged


from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.keyboards.sections import kb_earn, kb_help
from locales.ru import T


router = Router(name="sections")


@router.callback_query(F.data == "sec:earn")
async def cb_earn(callback: CallbackQuery) -> None:
    if callback.message is not None:
        with ignore_unchanged():
            await callback.message.edit_text(
                T.section_earn_caption,
                reply_markup=kb_earn(),
                parse_mode="HTML",
            )
    await callback.answer()


@router.callback_query(F.data == "sec:help")
async def cb_help(callback: CallbackQuery) -> None:
    if callback.message is not None:
        with ignore_unchanged():
            await callback.message.edit_text(
                T.section_help_caption,
                reply_markup=kb_help(),
                parse_mode="HTML",
            )
    await callback.answer()

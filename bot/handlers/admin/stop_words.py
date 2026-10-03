"""Админка: стоп-слова фильтра отзывов (доделка Этапа 8)."""

from __future__ import annotations

from contextlib import suppress

from aiogram import F, Router, html
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.filters.admin import IsAdmin
from bot.keyboards.admin_panel import kb_stop_words, kb_sw_cancel
from bot.states.admin import StopWordStates
from db.repositories.stop_word import StopWordRepo
from locales.ru import T


router = Router(name="admin_stop_words")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


def _render_root(words: list[str]) -> str:
    shown = "  ·  ".join(html.quote(w) for w in words[:50]) if words else T.admin_sw_empty
    return T.admin_sw_root.format(count=len(words), words=shown)


@router.callback_query(F.data == "adm:sw")
async def cb_open(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    if callback.message is None:
        await callback.answer()
        return
    words = await StopWordRepo(session).get_words()
    with suppress(TelegramAPIError):
        await callback.message.edit_text(_render_root(words), reply_markup=kb_stop_words())
    await callback.answer()


@router.callback_query(F.data == "adm:sw:add")
async def cb_add(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        await callback.answer()
        return
    await state.set_state(StopWordStates.waiting_add)
    with suppress(TelegramAPIError):
        await callback.message.edit_text(T.admin_sw_add_prompt, reply_markup=kb_sw_cancel())
    await callback.answer()


@router.callback_query(F.data == "adm:sw:rm")
async def cb_remove(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        await callback.answer()
        return
    await state.set_state(StopWordStates.waiting_remove)
    with suppress(TelegramAPIError):
        await callback.message.edit_text(T.admin_sw_remove_prompt, reply_markup=kb_sw_cancel())
    await callback.answer()


@router.message(StopWordStates.waiting_add, F.text)
async def msg_add(message: Message, state: FSMContext, session: AsyncSession) -> None:
    raw = [w.strip().lower() for w in (message.text or "").split(",")]
    words = [w for w in raw if w]
    if not words:
        await message.answer(T.admin_sw_add_prompt)
        return
    repo = StopWordRepo(session)
    added = await repo.add_bulk(words)
    await state.clear()
    all_words = await repo.get_words()
    await message.answer(
        T.admin_sw_added.format(count=added) + "\n\n" + _render_root(all_words),
        reply_markup=kb_stop_words(),
    )


@router.message(StopWordStates.waiting_remove, F.text)
async def msg_remove(message: Message, state: FSMContext, session: AsyncSession) -> None:
    word = (message.text or "").strip().lower()
    repo = StopWordRepo(session)
    removed = await repo.remove(word)
    await state.clear()
    all_words = await repo.get_words()
    prefix = T.admin_sw_removed if removed else T.admin_sw_not_found
    await message.answer(
        prefix + "\n\n" + _render_root(all_words), reply_markup=kb_stop_words()
    )

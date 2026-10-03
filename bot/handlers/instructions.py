"""Хендлер: Инструкция для пользователя."""
from __future__ import annotations

from utils.telegram import ignore_unchanged


from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.instructions import kb_instruction_page
from db.repositories.instruction import InstructionRepo
from locales.ru import T
from utils.ui import html_text


router = Router(name="instructions")


async def _edit_instruction_page(
    callback: CallbackQuery, *, page, page_idx: int, total: int
) -> None:
    """Показывает страницу и не оставляет экран мёртвым при ошибочном HTML."""
    if callback.message is None:
        return
    markup = kb_instruction_page(page_idx, total)
    text = T.ins_page_template.format(
        title=html_text(page.title),
        body=page.body,
        step=f"Шаг {page_idx + 1}",
        total=total,
    )
    try:
        await callback.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    except TelegramBadRequest:
        # Старые/ручные страницы могли содержать битую или неподдерживаемую
        # Telegram HTML-разметку. Показываем безопасный текстовый preview.
        safe_body = html_text(page.body[:600])
        with ignore_unchanged():
            await callback.message.edit_text(
                T.ins_page_template.format(
                    title=html_text(page.title),
                    body=safe_body,
                    step=f"Шаг {page_idx + 1}",
                    total=total,
                ),
                reply_markup=markup,
                parse_mode="HTML",
            )


@router.callback_query(F.data == "ins:open")
async def cb_instructions_open(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if callback.message is None:
        return
    repo = InstructionRepo(session)
    pages = await repo.get_active()
    if not pages:
        await callback.answer(T.ins_empty_alert, show_alert=True)
        return
    page = pages[0]
    await state.update_data(ins_page=0, ins_total=len(pages))
    await _edit_instruction_page(callback, page=page, page_idx=0, total=len(pages))
    await callback.answer()


@router.callback_query(F.data == "ins:noop")
async def cb_instructions_noop(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data.startswith("ins:page:"))
async def cb_instructions_page(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if callback.message is None:
        return
    try:
        delta = int((callback.data or "").split(":")[2])
    except (IndexError, ValueError):
        await callback.answer(T.stale_screen_alert, show_alert=True)
        return
    data = await state.get_data()
    page_idx = (data.get("ins_page", 0) + delta) % data.get("ins_total", 1)

    repo = InstructionRepo(session)
    pages = await repo.get_active()
    if not pages or page_idx >= len(pages):
        await callback.answer(T.stale_screen_alert, show_alert=True)
        return
    page = pages[page_idx]
    await state.update_data(ins_page=page_idx)
    await _edit_instruction_page(
        callback, page=page, page_idx=page_idx, total=len(pages)
    )
    await callback.answer()

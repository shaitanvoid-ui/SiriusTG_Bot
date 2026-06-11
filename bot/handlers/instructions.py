"""Хендлер: Инструкция для пользователя."""
from __future__ import annotations

from contextlib import suppress

from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.instructions import kb_instruction_page
from db.repositories.instruction import InstructionRepo
from locales.ru import T


router = Router(name="instructions")


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
        await callback.answer("📖 Скоро здесь появится инструкция.", show_alert=True)
        return
    page = pages[0]
    await state.update_data(ins_page=0, ins_total=len(pages))
    with suppress(Exception):
        await callback.message.edit_text(
            T.ins_page_template.format(
                title=page.title,
                body=page.body,
                step="Шаг 1",
                total=len(pages),
            ),
            reply_markup=kb_instruction_page(0, len(pages)),
            parse_mode="HTML",
        )
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
    delta = int(callback.data.split(":")[2])
    data = await state.get_data()
    page_idx = (data.get("ins_page", 0) + delta) % data.get("ins_total", 1)

    repo = InstructionRepo(session)
    pages = await repo.get_active()
    if not pages or page_idx >= len(pages):
        return
    page = pages[page_idx]
    await state.update_data(ins_page=page_idx)
    with suppress(Exception):
        await callback.message.edit_text(
            T.ins_page_template.format(
                title=page.title,
                body=page.body,
                step=f"Шаг {page_idx + 1}",
                total=len(pages),
            ),
            reply_markup=kb_instruction_page(page_idx, len(pages)),
            parse_mode="HTML",
        )
    await callback.answer()

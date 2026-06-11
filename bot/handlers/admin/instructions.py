"""Админка: редактор страниц инструкции (доделка Этапа 8).

CRUD: список → карточка → правка заголовка/текста, добавление (FSM 2 шага),
удаление (soft — is_active=False).
"""

from __future__ import annotations

from contextlib import suppress

from aiogram import F, Router, html
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.filters.admin import IsAdmin
from bot.keyboards.admin_panel import kb_ins_cancel, kb_ins_card, kb_ins_list
from bot.states.admin import InstructionStates
from db.repositories.instruction import InstructionRepo
from locales.ru import T


router = Router(name="admin_instructions")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


async def _render_list(message, session: AsyncSession) -> None:
    pages = await InstructionRepo(session).get_active()
    text = T.admin_ins_root.format(count=len(pages))
    with suppress(Exception):
        await message.edit_text(text, reply_markup=kb_ins_list(pages))


@router.callback_query(F.data == "adm:ins:list")
async def cb_list(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    if callback.message is not None:
        await _render_list(callback.message, session)
    await callback.answer()


@router.callback_query(F.data.startswith("adm:ins:open:"))
async def cb_open(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.data is None or callback.message is None:
        await callback.answer()
        return
    page_id = int(callback.data.rsplit(":", 1)[-1])
    page = await InstructionRepo(session).get_by_id(page_id)
    if page is None or not page.is_active:
        await callback.answer(T.admin_ins_deleted, show_alert=True)
        return
    text = T.admin_ins_card.format(id=page.id, title=html.quote(page.title), body=page.body)
    with suppress(Exception):
        await callback.message.edit_text(text[:4000], reply_markup=kb_ins_card(page.id))
    await callback.answer()


# ---------- добавление ----------

@router.callback_query(F.data == "adm:ins:add")
async def cb_add(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        await callback.answer()
        return
    await state.set_state(InstructionStates.waiting_new_title)
    with suppress(Exception):
        await callback.message.edit_text(
            T.admin_ins_new_title_prompt, reply_markup=kb_ins_cancel()
        )
    await callback.answer()


@router.message(InstructionStates.waiting_new_title, F.text)
async def msg_new_title(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not title:
        await message.answer(T.admin_ins_invalid)
        return
    await state.update_data(ins_title=title)
    await state.set_state(InstructionStates.waiting_new_body)
    await message.answer(
        T.admin_ins_new_body_prompt.format(title=html.quote(title)),
        reply_markup=kb_ins_cancel(),
    )


@router.message(InstructionStates.waiting_new_body, F.text)
async def msg_new_body(message: Message, state: FSMContext, session: AsyncSession) -> None:
    body = (message.text or "").strip()
    if not body:
        await message.answer(T.admin_ins_invalid)
        return
    data = await state.get_data()
    title = data.get("ins_title", "")
    repo = InstructionRepo(session)
    count = await repo.count()
    page = await repo.create(title=title, body=body, sort_order=count + 1)
    await state.clear()
    pages = await repo.get_active()
    await message.answer(
        T.admin_ins_created.format(title=html.quote(page.title)),
        reply_markup=kb_ins_list(pages),
    )


# ---------- правка ----------

@router.callback_query(F.data.startswith("adm:ins:et:"))
async def cb_edit_title(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.data is None or callback.message is None:
        await callback.answer()
        return
    page_id = int(callback.data.rsplit(":", 1)[-1])
    page = await InstructionRepo(session).get_by_id(page_id)
    if page is None:
        await callback.answer(T.admin_ins_deleted, show_alert=True)
        return
    await state.set_state(InstructionStates.waiting_edit_title)
    await state.update_data(ins_id=page_id)
    with suppress(Exception):
        await callback.message.edit_text(
            T.admin_ins_edit_title_prompt.format(title=html.quote(page.title)),
            reply_markup=kb_ins_cancel(),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("adm:ins:eb:"))
async def cb_edit_body(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.data is None or callback.message is None:
        await callback.answer()
        return
    page_id = int(callback.data.rsplit(":", 1)[-1])
    page = await InstructionRepo(session).get_by_id(page_id)
    if page is None:
        await callback.answer(T.admin_ins_deleted, show_alert=True)
        return
    await state.set_state(InstructionStates.waiting_edit_body)
    await state.update_data(ins_id=page_id)
    with suppress(Exception):
        await callback.message.edit_text(
            T.admin_ins_edit_body_prompt.format(title=html.quote(page.title)),
            reply_markup=kb_ins_cancel(),
        )
    await callback.answer()


@router.message(InstructionStates.waiting_edit_title, F.text)
async def msg_edit_title(message: Message, state: FSMContext, session: AsyncSession) -> None:
    title = (message.text or "").strip()
    if not title:
        await message.answer(T.admin_ins_invalid)
        return
    data = await state.get_data()
    repo = InstructionRepo(session)
    await repo.update(int(data["ins_id"]), title=title, body=None)
    await state.clear()
    pages = await repo.get_active()
    await message.answer(T.admin_ins_saved, reply_markup=kb_ins_list(pages))


@router.message(InstructionStates.waiting_edit_body, F.text)
async def msg_edit_body(message: Message, state: FSMContext, session: AsyncSession) -> None:
    body = (message.text or "").strip()
    if not body:
        await message.answer(T.admin_ins_invalid)
        return
    data = await state.get_data()
    repo = InstructionRepo(session)
    await repo.update(int(data["ins_id"]), title=None, body=body)
    await state.clear()
    pages = await repo.get_active()
    await message.answer(T.admin_ins_saved, reply_markup=kb_ins_list(pages))


# ---------- удаление ----------

@router.callback_query(F.data.startswith("adm:ins:del:"))
async def cb_delete(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.data is None or callback.message is None:
        await callback.answer()
        return
    page_id = int(callback.data.rsplit(":", 1)[-1])
    await InstructionRepo(session).delete(page_id)
    await callback.answer(T.admin_ins_deleted, show_alert=False)
    await _render_list(callback.message, session)

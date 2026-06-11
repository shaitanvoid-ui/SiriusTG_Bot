from __future__ import annotations

from contextlib import suppress

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.flow import count_total_steps, render_terms_page, show_captcha
from db.repositories.action_log import ActionLogRepo
from db.repositories.user import UserRepo
from locales.ru import T


router = Router(name="terms")


@router.callback_query(F.data.startswith("terms:p:"))
async def cb_terms_page(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if callback.message is None or callback.data is None:
        await callback.answer()
        return
    try:
        page = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer()
        return

    data = await state.get_data()
    total_steps = int(data.get("total_steps") or await count_total_steps(session))
    text, kb = render_terms_page(page=page, total_steps=total_steps)
    with suppress(Exception):
        await callback.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
    await callback.answer()


@router.callback_query(F.data == "terms:accept")
async def cb_accept_terms(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer()
        return
    await UserRepo(session).mark_terms_accepted(callback.from_user.id)
    await ActionLogRepo(session).log(
        user_tg_id=callback.from_user.id, action="terms_accepted"
    )
    await callback.answer("✅")
    # удаляем сообщение соглашения — оставляем чат чистым
    with suppress(Exception):
        await callback.message.delete()
    total_steps = await count_total_steps(session)
    await show_captcha(callback.message, state, total_steps=total_steps)


@router.callback_query(F.data == "terms:decline")
async def cb_decline_terms(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        await callback.answer()
        return
    await state.clear()
    with suppress(Exception):
        await callback.message.edit_text(T.terms_declined)
    await callback.answer()

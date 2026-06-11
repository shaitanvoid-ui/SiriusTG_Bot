"""Промокоды для юзера — вход из Профиля.

FSM: `prof:open` → 🎟 → intro-карточка → «Ввести код» → ждём текст → результат.
При honeypot-промокоде → soft-ban + отдельный текст.
"""

from __future__ import annotations

from contextlib import suppress

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.promo import kb_promo_intro, kb_promo_result, kb_promo_waiting
from bot.states.promo import PromoStates
from db.models import User
from db.repositories.user import UserRepo
from locales.ru import T
from services.promo import PromoService, PromoStatus
from services.settings import SettingsService
from utils.ui import stars


router = Router(name="promo")


@router.callback_query(F.data == "promo:open")
async def cb_open(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    await state.clear()
    if callback.message is None:
        await callback.answer()
        return
    max_len = await PromoService(session, SettingsService(session)).max_code_length()
    text = T.promo_intro.format(max_len=max_len)
    with suppress(Exception):
        await callback.message.edit_text(text, reply_markup=kb_promo_intro())
    await callback.answer()


@router.callback_query(F.data == "promo:start")
async def cb_start(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        await callback.answer()
        return
    await state.set_state(PromoStates.waiting_code)
    with suppress(Exception):
        await callback.message.edit_text(T.promo_waiting, reply_markup=kb_promo_waiting())
    await callback.answer()


@router.callback_query(F.data == "promo:cancel")
async def cb_cancel(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    await state.clear()
    if callback.message is None:
        await callback.answer()
        return
    max_len = await PromoService(session, SettingsService(session)).max_code_length()
    text = T.promo_intro.format(max_len=max_len)
    with suppress(Exception):
        await callback.message.edit_text(text, reply_markup=kb_promo_intro())
    await callback.answer()


@router.message(PromoStates.waiting_code, F.text)
async def msg_code(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    db_user: User | None = None,
) -> None:
    if message.from_user is None:
        return
    user = db_user or await UserRepo(session).get_by_tg_id(message.from_user.id)
    if user is None:
        return

    svc = PromoService(session, SettingsService(session))
    raw = message.text or ""
    res = await svc.redeem(user=user, raw_code=raw)

    # удалим введённое юзером сообщение, чтобы не засорять чат
    with suppress(Exception):
        await message.delete()

    await state.clear()

    if res.status == PromoStatus.OK:
        text = T.promo_ok.format(
            code=res.code,
            reward=stars(res.reward),
            balance=stars(res.balance),
        )
    elif res.status == PromoStatus.HONEYPOT_BANNED:
        text = T.promo_honeypot_banned
        await message.answer(text)
        return
    elif res.status == PromoStatus.NOT_FOUND:
        text = T.promo_not_found
    elif res.status == PromoStatus.ALREADY_USED:
        text = T.promo_already_used
    elif res.status == PromoStatus.EXPIRED:
        text = T.promo_expired
    elif res.status == PromoStatus.EXHAUSTED:
        text = T.promo_exhausted
    elif res.status == PromoStatus.INACTIVE:
        text = T.promo_inactive
    elif res.status == PromoStatus.TOO_LONG:
        text = T.promo_too_long
    elif res.status == PromoStatus.EMPTY:
        text = T.promo_empty
    else:
        text = T.error_generic

    await message.answer(text, reply_markup=kb_promo_result())

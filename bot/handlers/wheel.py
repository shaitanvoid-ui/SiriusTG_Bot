"""Колесо фортуны — экран и вращение (бесплатное/платное).

Edit-in-place: одна карточка обновляется после каждого вращения.
"""

from __future__ import annotations

from utils.telegram import ignore_unchanged

import asyncio
import secrets
import time

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.wheel import kb_paid_confirmation, kb_wheel
from db.models import User
from db.money import from_units, settlement_units
from db.repositories.user import UserRepo
from locales.ru import T
from services.settings import SettingsService
from services.wheel import SpinStatus, WheelResult, WheelService, WheelView
from utils.ui import stars


router = Router(name="wheel")


def _render(view: WheelView, *, result_line: str) -> str:
    free_state = T.wheel_free_yes if view.free_available else T.wheel_free_no
    sectors = (
        "  ·  ".join(stars(s) for s in view.sectors)
        if view.sectors
        else T.wheel_sectors_empty
    )
    return T.wheel_caption.format(
        free_state=free_state,
        cost=stars(view.cost),
        balance=stars(view.balance),
        sectors=sectors,
        result_line=result_line,
    )


async def _send_card(callback: CallbackQuery, view: WheelView, *, result_line: str) -> None:
    if callback.message is None:
        return
    text = _render(view, result_line=result_line)
    kb = kb_wheel(free_available=view.free_available, can_pay=view.can_pay, cost=view.cost)
    with ignore_unchanged():
        await callback.message.edit_text(text, reply_markup=kb)


async def _play_spin_animation(callback: CallbackQuery) -> None:
    """Короткая анимация вращения: кадры edit-in-place без клавиатуры.

    Клавиатура снимается на время анимации — защита от двойного спина.
    """
    if callback.message is None:
        return
    for frame in T.wheel_spin_frames:
        with ignore_unchanged():
            await callback.message.edit_text(frame)
        await asyncio.sleep(0.45)


async def _resolve(callback: CallbackQuery, session: AsyncSession, db_user: User | None) -> User | None:
    if callback.from_user is None or callback.message is None:
        return None
    return db_user or await UserRepo(session).get_by_tg_id(callback.from_user.id)


@router.callback_query(F.data == "whl:open")
async def cb_open(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User | None = None,
) -> None:
    user = await _resolve(callback, session, db_user)
    if user is None:
        await callback.answer()
        return
    svc = WheelService(session, SettingsService(session))
    if not await svc.settings.get_bool("wheel.enabled", True):
        await callback.answer(T.wheel_disabled_alert, show_alert=True)
        return
    view = await svc.get_view(user)
    await _send_card(callback, view, result_line=T.wheel_idle_line)
    await callback.answer()


@router.callback_query(F.data == "whl:noop")
async def cb_noop(callback: CallbackQuery) -> None:
    """Понятный ответ для заблокированной кнопки платного вращения."""
    await callback.answer(T.wheel_not_enough_alert, show_alert=True)


@router.callback_query(F.data.startswith("whl:spin:"))
async def cb_spin(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    db_user: User | None = None,
) -> None:
    if callback.data not in {"whl:spin:free", "whl:spin:paid"}:
        await callback.answer(T.stale_screen_alert, show_alert=True)
        return
    paid = callback.data.rsplit(":", 1)[-1] == "paid"
    if paid:
        # Legacy keyboards also require a fresh, priced confirmation.
        await cb_paid_confirmation(callback, session, state, db_user)
        return

    user = await _resolve(callback, session, db_user)
    if user is None:
        await callback.answer()
        return

    svc = WheelService(session, SettingsService(session))
    result: WheelResult = await svc.spin(user, paid=paid)

    await _present_result(callback, session, svc, result)


async def _present_result(callback: CallbackQuery, session: AsyncSession, svc: WheelService,
                          result: WheelResult) -> None:
    user = await UserRepo(session).get_by_tg_id(callback.from_user.id)
    if user is None:
        await callback.answer()
        return
    if result.status == SpinStatus.BLOCKED:
        await callback.answer(T.reward_restricted, show_alert=True)
        return

    if result.status == SpinStatus.ALREADY:
        await callback.answer(T.stale_screen_alert, show_alert=True)
        return

    if result.status == SpinStatus.DISABLED:
        await callback.answer(T.wheel_disabled_alert, show_alert=True)
        return

    if result.status == SpinStatus.NO_FREE:
        view = await svc.get_view(user)
        await _send_card(callback, view, result_line=T.wheel_idle_line)
        await callback.answer(T.wheel_no_free_alert, show_alert=True)
        return

    if result.status == SpinStatus.NOT_ENOUGH:
        view = await svc.get_view(user)
        await _send_card(callback, view, result_line=T.wheel_idle_line)
        await callback.answer(T.wheel_not_enough_alert, show_alert=True)
        return

    # Commit the outcome before presentation: a Telegram failure cannot reroll it,
    # and the animation no longer holds SQLite's global writer lock.
    await session.commit()
    await callback.answer()
    await _play_spin_animation(callback)
    view = await svc.get_view(user)
    if result.prize > 0:
        result_line = T.wheel_win_line.format(prize=stars(result.prize))
    else:
        result_line = T.wheel_empty_line
    await _send_card(callback, view, result_line=result_line)


@router.callback_query(F.data == "whl:confirm")
async def cb_paid_confirmation(callback: CallbackQuery, session: AsyncSession, state: FSMContext,
                               db_user: User | None = None) -> None:
    user = await _resolve(callback, session, db_user)
    if user is None:
        await callback.answer()
        return
    svc = WheelService(session, SettingsService(session))
    if not await svc.settings.get_bool("wheel.enabled", True):
        await callback.answer(T.wheel_disabled_alert, show_alert=True)
        return
    view = await svc.get_view(user)
    if not view.can_pay:
        await callback.answer(T.wheel_not_enough_alert, show_alert=True)
        return
    token = secrets.token_urlsafe(12)
    await state.clear()
    await state.update_data(wheel_paid_token=token, wheel_paid_cost=view.cost,
                            wheel_paid_expires_at=int(time.time()) + 120)
    with ignore_unchanged():
        await callback.message.edit_text(T.wheel_paid_confirmation.format(cost=stars(view.cost), balance=stars(view.balance)),
                                         reply_markup=kb_paid_confirmation(token=token, cost=view.cost))
    await callback.answer()


@router.callback_query(F.data.startswith("whl:paid:"))
async def cb_paid(callback: CallbackQuery, session: AsyncSession, state: FSMContext,
                  db_user: User | None = None) -> None:
    data = await state.get_data()
    token = (callback.data or "").split(":", 2)[-1]
    if token != data.get("wheel_paid_token") or int(data.get("wheel_paid_expires_at") or 0) < time.time():
        await callback.answer(T.stale_screen_alert, show_alert=True)
        return
    user = await _resolve(callback, session, db_user)
    if user is None:
        await callback.answer()
        return
    svc = WheelService(session, SettingsService(session))
    cost = float(from_units(settlement_units(await svc.settings.get_float("wheel.cost", 1.0))))
    if cost != data.get("wheel_paid_cost"):
        await state.clear()
        await callback.answer(T.wheel_price_changed_alert, show_alert=True)
        return
    await state.clear()
    result = await svc.spin(user, paid=True, request_token=token)
    await _present_result(callback, session, svc, result)

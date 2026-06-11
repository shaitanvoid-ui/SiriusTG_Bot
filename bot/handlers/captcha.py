from __future__ import annotations

from contextlib import suppress

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.flow import count_total_steps, show_captcha, show_subs
from bot.states.onboarding import OnboardingStates
from db.repositories.action_log import ActionLogRepo
from db.repositories.user import UserRepo
from locales.ru import T


router = Router(name="captcha")


@router.callback_query(
    OnboardingStates.awaiting_captcha,
    F.data.startswith("cap:"),
)
async def cb_captcha_choice(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if callback.from_user is None or callback.data is None or callback.message is None:
        await callback.answer()
        return

    try:
        _, token, picked = callback.data.split(":", 2)
    except ValueError:
        await callback.answer()
        return

    data = await state.get_data()
    expected_token = data.get("captcha_token")
    expected_answer = data.get("captcha_answer")
    attempts_left = int(data.get("captcha_attempts_left", 0))

    if token != expected_token:
        await callback.answer()
        return

    total_steps = int(data.get("total_steps") or await count_total_steps(session))

    if picked == expected_answer:
        user_repo = UserRepo(session)
        await user_repo.mark_captcha_passed(callback.from_user.id)
        await ActionLogRepo(session).log(
            user_tg_id=callback.from_user.id, action="captcha_ok"
        )
        await callback.answer(T.captcha_ok)
        # удаляем сообщение с капчей — оставляем чат чистым
        with suppress(Exception):
            await callback.message.delete()
        user = await user_repo.get_by_tg_id(callback.from_user.id)
        if user is None:
            return
        await show_subs(callback.message, state, session, user=user, total_steps=total_steps)
        return

    attempts_left -= 1
    if attempts_left <= 0:
        await ActionLogRepo(session).log(
            user_tg_id=callback.from_user.id, action="captcha_failed"
        )
        await state.clear()
        await callback.answer(T.captcha_failed, show_alert=True)
        with suppress(Exception):
            await callback.message.edit_reply_markup(reply_markup=None)
        return

    await state.update_data(captcha_attempts_left=attempts_left)
    await callback.answer(T.captcha_wrong.format(left=attempts_left), show_alert=True)
    with suppress(Exception):
        await callback.message.delete()
    await show_captcha(callback.message, state, total_steps=total_steps)

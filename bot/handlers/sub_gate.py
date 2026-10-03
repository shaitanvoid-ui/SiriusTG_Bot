from __future__ import annotations

from utils.telegram import ignore_unchanged


from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.flow import finalize_subs_passed, notify_referrer_reward, show_main_menu
from db.repositories.sponsor import SponsorRepo
from db.repositories.user import UserRepo
from db.repositories.user_subscription import UserSubscriptionRepo
from locales.ru import T
from services.sponsor import SponsorService


router = Router(name="sub_gate")


@router.callback_query(F.data == "subs:check")
async def cb_check_subs(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer()
        return

    user_repo = UserRepo(session)
    db_user = await user_repo.get_by_tg_id(callback.from_user.id)
    if db_user is None:
        await callback.answer()
        return

    service = SponsorService(SponsorRepo(session), UserSubscriptionRepo(session))
    all_ok, results = await service.check_user(
        callback.bot, tg_id=callback.from_user.id, user_id=db_user.id, force=True
    )
    if not all_ok:
        text = (
            T.subs_not_subscribed
            if any(result.is_definitively_not_subscribed for result in results)
            else T.subs_check_unavailable
        )
        await callback.answer(text, show_alert=True)
        return

    reward_event = await finalize_subs_passed(session=session, user=db_user)

    await callback.answer(T.subs_all_ok)
    with ignore_unchanged():
        await callback.message.edit_reply_markup(reply_markup=None)
    await state.clear()
    await show_main_menu(callback.message, session, user=db_user)

    if reward_event is not None:
        await notify_referrer_reward(callback.bot, reward_event)

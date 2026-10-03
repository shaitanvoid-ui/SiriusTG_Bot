"""Хендлер админки отзывов — модерация (Этап 8)."""
from __future__ import annotations

from contextlib import suppress

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.filters.admin import IsAdmin
from bot.keyboards.admin_reviews import kb_reviews_list, kb_review_mod_actions
from bot.states.admin_reviews import ReviewModStates
from core.config import settings
from db.repositories.review import ReviewRepo
from db.repositories.user import UserRepo
from db.repositories.action_log import ActionLogRepo
from services.reviews import ReviewService
from services.settings import SettingsService
from locales.ru import T
from utils.tz import fmt_dt
from utils.ui import html_text


router = Router(name="admin_reviews")
router.callback_query.filter(IsAdmin())
router.message.filter(IsAdmin())


@router.callback_query(F.data == "adm:rev:list")
async def cb_reviews_list(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.message is None:
        return
    repo = ReviewRepo(session)
    pending = await repo.get_pending(limit=50)

    if not pending:
        with suppress(TelegramAPIError):
            await callback.message.edit_text(
                T.admin_reviews_empty,
                reply_markup=kb_reviews_list(),
            )
        await callback.answer()
        return

    review = pending[0]
    user_repo = UserRepo(session)
    db_user = await user_repo.get_by_id(review.user_id)
    stars = "⭐" * review.rating
    user_info = (
        f"@{html_text(db_user.username)}" if db_user and db_user.username else
        f"<code>{db_user.tg_id}</code>" if db_user else "<code>?</code>"
    )
    text = T.review_mod_card.format(
        id=review.id,
        user_info=user_info,
        rating_stars=f"{stars} {review.rating}/5",
        is_anon=T.review_mod_anonymous if review.is_anonymous else T.review_mod_public,
        date=fmt_dt(review.created_at),
        text=html_text(review.text[:300]),
    )
    with suppress(TelegramAPIError):
        await callback.message.edit_text(
            text,
            reply_markup=kb_review_mod_actions(review.id),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("adm:rev:approve:"))
async def cb_review_approve(callback: CallbackQuery, bot: Bot, session: AsyncSession) -> None:
    review_id = int(callback.data.split(":")[-1])
    svc = ReviewService(session=session)
    review, action_key = await svc.moderate(review_id, "approve")
    if review is None:
        await callback.answer(T.review_already_done, show_alert=True)
        return

    await ActionLogRepo(session).log(
        user_tg_id=callback.from_user.id if callback.from_user else None,
        action="review_approved",
        payload={"review_id": review_id},
    )

    # публикация в канал отзывов + DM юзеру — после успешной модерации
    await svc.publish_review(bot, review)
    s = SettingsService(session)
    reward = await s.get_float("review.reward", 1.0)
    await svc.notify_user_approved(bot, review, reward)

    if settings.log_channel_id:
        await svc.notify_log(bot, review, action_key)

    with suppress(TelegramAPIError):
        if callback.message:
            await callback.message.edit_text(
                T.admin_review_approved,
                reply_markup=kb_reviews_list(),
            )
    await callback.answer()


@router.callback_query(F.data.startswith("adm:rev:reject:"))
async def cb_review_reject_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    review_id = int(callback.data.split(":")[-1])
    await state.update_data(mod_review_id=review_id, mod_action="reject")
    await state.set_state(ReviewModStates.waiting_note)
    if callback.message:
        with suppress(TelegramAPIError):
            await callback.message.edit_text(
                T.review_reject_confirm.format(id=review_id),
            )
    await callback.answer()


@router.callback_query(F.data.startswith("adm:rev:convert:"))
async def cb_review_convert_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    review_id = int(callback.data.split(":")[-1])
    await state.update_data(mod_review_id=review_id, mod_action="convert")
    await state.set_state(ReviewModStates.waiting_note)
    if callback.message:
        with suppress(TelegramAPIError):
            await callback.message.edit_text(
                T.review_convert_confirm.format(id=review_id),
            )
    await callback.answer()


@router.message(F.text, ReviewModStates.waiting_note)
async def cb_review_mod_note(
    message: Message, bot: Bot, state: FSMContext, session: AsyncSession
) -> None:
    note = (message.text or "").strip()
    data = await state.get_data()
    review_id = data.get("mod_review_id")
    action = data.get("mod_action", "reject")
    if review_id is None:
        await state.clear()
        with suppress(TelegramAPIError):
            await message.answer(T.review_not_found, reply_markup=kb_reviews_list())
        return

    svc = ReviewService(session=session)
    review, action_key = await svc.moderate(review_id, action, note)
    if review is None:
        await state.clear()
        with suppress(TelegramAPIError):
            await message.answer(T.review_already_done, reply_markup=kb_reviews_list())
        return

    if settings.log_channel_id:
        await svc.notify_log(bot, review, action_key)

    if action == "convert":
        with suppress(TelegramAPIError):
            await message.answer(T.review_convert_done, reply_markup=kb_reviews_list())
    else:
        with suppress(TelegramAPIError):
            await message.answer(T.review_reject_done, reply_markup=kb_reviews_list())
    await state.clear()

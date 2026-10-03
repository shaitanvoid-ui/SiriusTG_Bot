"""Хендлер отзывов — FSM flow (Этап 8)."""
from __future__ import annotations

from utils.telegram import ignore_unchanged

from contextlib import suppress

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.states.reviews import ReviewStates
from bot.keyboards.reviews import (
    kb_review_anonymity,
    kb_review_confirm,
    kb_review_intro,
    kb_review_rating,
    kb_review_success,
    kb_review_text_step,
)
from bot.keyboards.sections import kb_help
from core.config import settings as app_settings
from db.models import User
from services.reviews import ReviewService
from services.settings import SettingsService
from locales.ru import T
from utils.ui import html_text


router = Router(name="reviews")


def _stars_line(rating: int) -> str:
    return "⭐" * rating + "☆" * (5 - rating)


def _preview(text: str, *, limit: int = 100) -> str:
    clipped = text[:limit] + ("…" if len(text) > limit else "")
    return f"<i>{html_text(clipped)}</i>"


async def _edit_state_card(
    message: Message,
    state: FSMContext,
    text: str,
    reply_markup,
) -> None:
    """Сохранять FSM в одной карточке и не оставлять устаревшие экраны."""
    data = await state.get_data()
    chat_id = data.get("ui_chat_id")
    message_id = data.get("ui_message_id")
    edited = False
    if chat_id and message_id:
        try:
            await message.bot.edit_message_text(
                text,
                chat_id=int(chat_id),
                message_id=int(message_id),
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
            edited = True
        except TelegramBadRequest:
            pass
    if not edited:
        sent = await message.answer(text, reply_markup=reply_markup, parse_mode="HTML")
        await state.update_data(ui_chat_id=sent.chat.id, ui_message_id=sent.message_id)
    with suppress(TelegramBadRequest):
        await message.delete()


@router.callback_query(F.data == "rev:intro")
async def cb_review_intro(callback: CallbackQuery, db_user: User, session: AsyncSession) -> None:
    if callback.message is None:
        return

    s = SettingsService(session)
    if not await s.get_bool("review.enabled", True):
        await callback.answer(T.reviews_disabled_alert, show_alert=True)
        return

    svc = ReviewService(session)
    ok, reason = await svc.check_antispam(db_user)
    if not ok:
        await callback.answer(
            T.review_antispam_fail_alert.format(reason=reason), show_alert=True
        )
        return

    min_refs = await s.get_int("review.antispam_min_refs", 3)
    cooldown_days = await s.get_int("review.antispam_cooldown_days", 7)
    min_len = await s.get_int("review.min_text_length", 30)
    max_len = await s.get_int("review.max_text_length", 500)
    reward = await s.get_float("review.reward", 1.0)

    text = T.review_intro.format(
        min_refs=min_refs,
        cooldown_days=cooldown_days,
        min_len=min_len,
        max_len=max_len,
        reward=reward,
    )
    with ignore_unchanged():
        await callback.message.edit_text(
            text,
            reply_markup=kb_review_intro(),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data == "rev:start")
async def cb_review_start(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        return
    await state.set_state(ReviewStates.rating)
    await state.update_data(
        rating=0,
        ui_chat_id=callback.message.chat.id,
        ui_message_id=callback.message.message_id,
    )
    with ignore_unchanged():
        await callback.message.edit_text(
            T.review_rating_page,
            reply_markup=kb_review_rating(0),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data.startswith("rev:star:"), ReviewStates.rating)
async def cb_review_star(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        return
    rating = int(callback.data.split(":")[2])
    await state.update_data(rating=rating)
    with ignore_unchanged():
        await callback.message.edit_reply_markup(reply_markup=kb_review_rating(rating))
    await callback.answer()


@router.callback_query(F.data == "rev:rating_next", ReviewStates.rating)
async def cb_review_rating_next(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.message is None:
        return
    data = await state.get_data()
    rating = data.get("rating", 0)
    if rating == 0:
        await callback.answer(T.review_rating_required_alert, show_alert=True)
        return
    await state.set_state(ReviewStates.text)

    s = SettingsService(session)
    min_len = await s.get_int("review.min_text_length", 30)
    max_len = await s.get_int("review.max_text_length", 500)
    rating_line = T.review_rating_stars.format(stars=_stars_line(rating), rating=rating)

    with ignore_unchanged():
        await callback.message.edit_text(
            T.review_text_page.format(rating_line=rating_line, min_len=min_len, max_len=max_len),
            reply_markup=kb_review_text_step(),
            parse_mode="HTML",
        )
    await callback.answer()


@router.message(F.text, ReviewStates.text)
async def cb_review_text(message: Message, state: FSMContext, session: AsyncSession) -> None:
    text_val = message.text.strip()
    svc = ReviewService(session)
    ok, reason = await svc.filter_text(text_val)
    if not ok:
        await _edit_state_card(
            message,
            state,
            T.review_filter_fail.format(reason=html_text(reason or T.error_generic)),
            kb_review_text_step(),
        )
        return

    await state.update_data(text=text_val)
    await state.set_state(ReviewStates.anonymity)
    data = await state.get_data()
    rating = data.get("rating", 0)
    rating_line = T.review_rating_stars.format(stars=_stars_line(rating), rating=rating)
    await _edit_state_card(
        message,
        state,
        T.review_anonymity_page.format(
            rating_line=rating_line,
            text_preview=_preview(text_val),
        ),
        kb_review_anonymity(),
    )


@router.callback_query(F.data.in_({"rev:anon_yes", "rev:anon_no"}), ReviewStates.anonymity)
async def cb_review_anonymity(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        return
    is_anon = callback.data == "rev:anon_yes"
    await state.update_data(is_anonymous=is_anon)
    await state.set_state(ReviewStates.confirm)

    data = await state.get_data()
    rating = data.get("rating", 0)
    text_val = data.get("text", "")
    rating_line = T.review_rating_stars.format(stars=_stars_line(rating), rating=rating)
    anon_line = T.review_anon_anon if is_anon else T.review_anon_public
    preview = _preview(text_val)

    with ignore_unchanged():
        await callback.message.edit_text(
            T.review_confirm_page.format(
                rating_line=rating_line,
                text_preview=preview,
                anon_line=anon_line,
            ),
            reply_markup=kb_review_confirm(),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data == "rev:confirm", ReviewStates.confirm)
async def cb_review_confirm(
    callback: CallbackQuery, db_user: User, state: FSMContext, session: AsyncSession, bot: Bot
) -> None:
    if callback.message is None:
        return

    data = await state.get_data()
    rating = data.get("rating", 0)
    text_val = data.get("text", "")
    is_anon = data.get("is_anonymous", False)

    svc = ReviewService(session)
    review, err = await svc.create_review(db_user, rating, text_val, is_anon)
    if not review:
        await callback.answer(
            T.review_filter_fail_alert.format(reason=str(err or T.error_generic)),
            show_alert=True,
        )
        await state.clear()
        with ignore_unchanged():
            await callback.message.edit_text(
                T.section_help_caption,
                reply_markup=kb_help(),
                parse_mode="HTML",
            )
        return

    s = SettingsService(session)
    reward = await s.get_float("review.reward", 1.0)
    reward_line = T.review_success_reward.format(reward=reward) if reward > 0 else ""

    with ignore_unchanged():
        await callback.message.edit_text(
            T.review_success.format(reward_line=reward_line),
            reply_markup=kb_review_success(),
            parse_mode="HTML",
        )
    await state.clear()
    await callback.answer()

    if app_settings.log_channel_id:
        with suppress(TelegramAPIError):
            await bot.send_message(
                app_settings.log_channel_id,
                T.log_review_submitted.format(tg_id=db_user.tg_id, rating=rating),
            )


@router.callback_query(F.data == "rev:cancel")
async def cb_review_cancel(
    callback: CallbackQuery, state: FSMContext
) -> None:
    await state.clear()
    if callback.message is not None:
        with ignore_unchanged():
            await callback.message.edit_text(
                T.section_help_caption,
                reply_markup=kb_help(),
                parse_mode="HTML",
            )
    await callback.answer()


@router.callback_query(F.data == "rev:back:rating", ReviewStates.text)
async def cb_review_back_rating(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        await callback.answer()
        return
    data = await state.get_data()
    rating = int(data.get("rating", 0))
    await state.set_state(ReviewStates.rating)
    with ignore_unchanged():
        await callback.message.edit_text(
            T.review_rating_page,
            reply_markup=kb_review_rating(rating),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data == "rev:back:text", ReviewStates.anonymity)
async def cb_review_back_text(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if callback.message is None:
        await callback.answer()
        return
    data = await state.get_data()
    rating = int(data.get("rating", 0))
    settings = SettingsService(session)
    await state.set_state(ReviewStates.text)
    with ignore_unchanged():
        await callback.message.edit_text(
            T.review_text_page.format(
                rating_line=T.review_rating_stars.format(
                    stars=_stars_line(rating), rating=rating
                ),
                min_len=await settings.get_int("review.min_text_length", 30),
                max_len=await settings.get_int("review.max_text_length", 500),
            ),
            reply_markup=kb_review_text_step(),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data == "rev:back:anon", ReviewStates.confirm)
async def cb_review_back_anonymity(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        await callback.answer()
        return
    data = await state.get_data()
    rating = int(data.get("rating", 0))
    await state.set_state(ReviewStates.anonymity)
    with ignore_unchanged():
        await callback.message.edit_text(
            T.review_anonymity_page.format(
                rating_line=T.review_rating_stars.format(
                    stars=_stars_line(rating), rating=rating
                ),
                text_preview=_preview(str(data.get("text", ""))),
            ),
            reply_markup=kb_review_anonymity(),
            parse_mode="HTML",
        )
    await callback.answer()


@router.message(ReviewStates.text)
async def msg_review_non_text(message: Message) -> None:
    await message.answer(T.review_text_input_required)


@router.callback_query(F.data.startswith("rev:"))
async def cb_review_stale(callback: CallbackQuery) -> None:
    await callback.answer(T.stale_screen_alert, show_alert=True)

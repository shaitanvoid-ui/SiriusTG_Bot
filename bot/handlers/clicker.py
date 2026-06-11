"""Кликер — экран и мини-капча.

Edit-in-place: одна и та же «карточка» обновляется при каждом тапе.
Мини-капча показывается на том же сообщении, после прохождения возвращаемся
к обычному виду карточки.
"""

from __future__ import annotations

from contextlib import suppress

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.clicker import kb_clicker, kb_clicker_captcha
from db.models import User
from db.repositories.user import UserRepo
from locales.ru import T
from services.clicker import (
    CaptchaStatus,
    ClickerService,
    ClickStatus,
    ClickerView,
)
from services.settings import SettingsService
from utils.ui import human_duration, progress_bar, stars


router = Router(name="clicker")


def _cooldown_line(view: ClickerView) -> str:
    if view.clicks >= view.daily_limit:
        return T.clicker_limit_line
    if view.cooldown_ms_left > 0:
        return T.clicker_cooldown_line.format(left=human_duration(view.cooldown_ms_left))
    return T.clicker_ready_line


def _render_card(view: ClickerView) -> str:
    bar = progress_bar(view.clicks, view.daily_limit)
    return T.clicker_caption.format(
        level_emoji=view.level.emoji,
        level_name=view.level.name,
        reward_per_click=stars(view.reward_per_click),
        clicks=view.clicks,
        daily_limit=view.daily_limit,
        earned_today=stars(view.earned_today),
        balance=stars(view.balance),
        progress_bar=bar,
        cooldown_line=_cooldown_line(view),
    )


def _render_captcha(hint: tuple[str, ...], *, wrong: bool = False) -> str:
    hint_line = "   ".join(hint)
    base = T.clicker_captcha_caption.format(hint=hint_line)
    if wrong:
        return T.clicker_captcha_wrong_prefix + base
    return base


async def _send_card(callback: CallbackQuery, view: ClickerView) -> None:
    if callback.message is None:
        return
    can_click = (
        view.clicks < view.daily_limit
        and not view.captcha_required
    )
    if view.captcha_required and view.captcha_token:
        text = _render_captcha(view.captcha_hint)
        kb = kb_clicker_captcha(view.captcha_token, view.captcha_choices)
    else:
        text = _render_card(view)
        kb = kb_clicker(can_click=can_click, cooldown_ms_left=view.cooldown_ms_left)
    with suppress(Exception):
        await callback.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data == "clk:open")
async def cb_open(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User | None = None,
) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer()
        return
    user = db_user or await UserRepo(session).get_by_tg_id(callback.from_user.id)
    if user is None:
        await callback.answer()
        return
    svc = ClickerService(session, SettingsService(session))
    view = await svc.get_view(user)
    await _send_card(callback, view)
    await callback.answer()


@router.callback_query(F.data == "clk:noop")
async def cb_noop(callback: CallbackQuery) -> None:
    await callback.answer(T.clicker_daily_limit_alert, show_alert=False)


@router.callback_query(F.data == "clk:tap")
async def cb_tap(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User | None = None,
) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer()
        return
    user = db_user or await UserRepo(session).get_by_tg_id(callback.from_user.id)
    if user is None:
        await callback.answer()
        return

    svc = ClickerService(session, SettingsService(session))
    result = await svc.click(user)

    if result.status == ClickStatus.TOO_FAST:
        # обновим карточку — таймер на кнопке/в тексте подтянется
        view = await svc.get_view(user)
        await _send_card(callback, view)
        await callback.answer(
            T.clicker_too_fast_alert.format(left=human_duration(result.retry_after_ms)),
            show_alert=False,
        )
        return

    if result.status == ClickStatus.DAILY_LIMIT:
        await callback.answer(T.clicker_daily_limit_alert, show_alert=False)
        # обновим карточку, чтобы кнопка переключилась на «лимит»
        view = await svc.get_view(user)
        await _send_card(callback, view)
        return

    if result.status == ClickStatus.NEED_CAPTCHA:
        await callback.answer(T.clicker_captcha_required_alert, show_alert=False)
        if callback.message is not None and result.captcha_token:
            with suppress(Exception):
                await callback.message.edit_text(
                    _render_captcha(result.captcha_hint),
                    reply_markup=kb_clicker_captcha(
                        result.captcha_token, result.captcha_choices
                    ),
                )
        return

    # OK
    if result.captcha_required and result.captcha_token:
        if callback.message is not None:
            with suppress(Exception):
                await callback.message.edit_text(
                    _render_captcha(result.captcha_hint),
                    reply_markup=kb_clicker_captcha(
                        result.captcha_token, result.captcha_choices
                    ),
                )
        await callback.answer(T.clicker_captcha_triggered_alert, show_alert=False)
        return

    # Edit-in-place нормальной карточки. Обычный тап — лёгкий тост,
    # каждые 10 тапов — веха, добитый лимит — полноценные «фанфары».
    view = await svc.get_view(user)
    await _send_card(callback, view)
    if view.clicks >= view.daily_limit:
        await callback.answer(
            T.clicker_finish_alert.format(earned=stars(view.earned_today)),
            show_alert=True,
        )
    elif view.clicks % 10 == 0:
        await callback.answer(
            T.clicker_milestone_alert.format(
                clicks=view.clicks, reward=stars(result.reward)
            )
        )
    else:
        await callback.answer(T.clicker_tick_alert.format(reward=stars(result.reward)))


@router.callback_query(F.data.startswith("clk:cap:"))
async def cb_captcha_choice(
    callback: CallbackQuery,
    session: AsyncSession,
    db_user: User | None = None,
) -> None:
    if callback.data is None or callback.from_user is None or callback.message is None:
        await callback.answer()
        return
    # формат: clk:cap:<token>:<emoji>
    parts = callback.data.split(":", 3)
    if len(parts) < 4:
        await callback.answer()
        return
    token, emoji = parts[2], parts[3]

    user = db_user or await UserRepo(session).get_by_tg_id(callback.from_user.id)
    if user is None:
        await callback.answer()
        return

    svc = ClickerService(session, SettingsService(session))
    res = await svc.submit_captcha(user, token=token, choice=emoji)

    if res.status == CaptchaStatus.OK:
        # сняли блок — рисуем обычную карточку
        view = await svc.get_view(user)
        await _send_card(callback, view)
        await callback.answer(T.clicker_captcha_ok_alert, show_alert=False)
        return

    if res.status == CaptchaStatus.EXPIRED:
        view = await svc.get_view(user)
        await _send_card(callback, view)
        await callback.answer(T.clicker_captcha_expired_alert, show_alert=False)
        return

    # WRONG — обновим капчу
    if res.captcha_token:
        with suppress(Exception):
            await callback.message.edit_text(
                _render_captcha(res.captcha_hint, wrong=True),
                reply_markup=kb_clicker_captcha(res.captcha_token, res.captcha_choices),
            )
    await callback.answer(T.clicker_captcha_wrong_alert, show_alert=False)

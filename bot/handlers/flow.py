"""Решает что показать юзеру в зависимости от пройденных гейтов."""

from __future__ import annotations

from contextlib import suppress

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession

from aiogram.types import InlineKeyboardMarkup

from bot.handlers.menu import render_main_menu_message
from bot.keyboards.onboarding import kb_captcha, kb_subs, kb_terms_page
from bot.states.onboarding import OnboardingStates
from core.config import settings as app_settings
from db.models import User
from db.repositories.action_log import ActionLogRepo
from db.repositories.sponsor import SponsorRepo
from db.repositories.user import UserRepo
from locales.ru import T
from services.partner import PartnerService
from services.referral import ReferralService, RewardEvent
from services.settings import SettingsService
from utils.captcha import generate_task
from utils.captcha_image import render as render_captcha_image
from utils.ui import stars


async def count_total_steps(session: AsyncSession) -> int:
    """2 шага если нет обяз. спонсоров, 3 если есть. Считается в момент старта онбординга."""
    sponsors = await SponsorRepo(session).list_required_active()
    return 3 if sponsors else 2


def _step_label(current: int, total: int) -> str:
    return f"Шаг {current} из {total}"


TERMS_TOTAL_PAGES: int = len(T.terms_pages_bodies)


def render_terms_page(*, page: int, total_steps: int) -> tuple[str, InlineKeyboardMarkup]:
    """Возвращает (текст, клавиатуру) для страницы соглашения."""
    page = max(1, min(TERMS_TOTAL_PAGES, page))
    body = T.terms_pages_bodies[page - 1]
    dots = "●" * page + "○" * (TERMS_TOTAL_PAGES - page)
    text = T.terms_page_template.format(
        step=_step_label(1, total_steps),
        dots=dots,
        page=page,
        total=TERMS_TOTAL_PAGES,
        body=body,
    )
    return text, kb_terms_page(page, TERMS_TOTAL_PAGES)


async def show_terms(message: Message, state: FSMContext, *, total_steps: int) -> None:
    await state.set_state(OnboardingStates.awaiting_terms)
    await state.update_data(total_steps=total_steps)
    text, kb = render_terms_page(page=1, total_steps=total_steps)
    await message.answer(text, reply_markup=kb, disable_web_page_preview=True)


async def show_captcha(message: Message, state: FSMContext, *, total_steps: int) -> None:
    task = generate_task()
    await state.set_state(OnboardingStates.awaiting_captcha)
    await state.update_data(
        captcha_token=task.token,
        captcha_answer=task.answer,
        captcha_attempts_left=3,
        total_steps=total_steps,
    )
    png = render_captcha_image(task.on_image)
    await message.answer_photo(
        photo=BufferedInputFile(png, filename="captcha.png"),
        caption=T.captcha_caption.format(step=_step_label(2, total_steps)),
        reply_markup=kb_captcha(task.choices, task.token),
    )


async def show_subs(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    *,
    user: User,
    total_steps: int,
) -> None:
    sponsors = await SponsorRepo(session).list_required_active()
    if not sponsors:
        # обязательных каналов нет — финализируем гейт сразу
        reward_event = await finalize_subs_passed(session=session, user=user)
        await state.clear()
        await show_main_menu(message, session, user=user)
        if reward_event is not None and message.bot is not None:
            await notify_referrer_reward(message.bot, reward_event)
        return
    await state.set_state(OnboardingStates.awaiting_subs)
    await message.answer(
        T.subs_caption.format(step=_step_label(total_steps, total_steps)),
        reply_markup=kb_subs(sponsors),
    )


async def show_main_menu(
    message: Message,
    session: AsyncSession,
    *,
    user: User,
) -> None:
    """Главное меню как новое сообщение (после онбординга / закрытия админки)."""
    await render_main_menu_message(message, session, user)


async def route_user(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    total_steps = await count_total_steps(session)
    if user.accepted_terms_at is None:
        await show_terms(message, state, total_steps=total_steps)
        return
    if user.captcha_passed_at is None:
        await show_captcha(message, state, total_steps=total_steps)
        return
    if user.subs_passed_at is None:
        await show_subs(message, state, session, user=user, total_steps=total_steps)
        return
    await state.clear()
    await show_main_menu(message, session, user=user)


# ---------- единая точка завершения spons-gate ----------

async def finalize_subs_passed(
    *,
    session: AsyncSession,
    user: User,
) -> RewardEvent | None:
    """Помечает subs_passed_at, логирует и вызывает реферальную награду.

    Идемпотентно: если subs_passed_at уже стоял — никаких побочных эффектов.
    Вызывается из sub_gate (юзер ткнул «Проверить») и из flow.show_subs
    (когда обязательных спонсоров нет вовсе).
    """
    if user.subs_passed_at is not None:
        return None
    await UserRepo(session).mark_subs_passed(user.tg_id)
    await ActionLogRepo(session).log(
        user_tg_id=user.tg_id, action="subs_passed"
    )
    settings_svc = SettingsService(session)
    # партнёрский CPA (Этап 10): юзер пришёл по UTM-ссылке и прошёл гейт
    await PartnerService(session, settings_svc).accrue_passed_user(user)
    ref_svc = ReferralService(session, settings_svc)
    return await ref_svc.on_user_passed_subs(user=user)


async def notify_referrer_reward(bot: Bot, event: RewardEvent) -> None:
    """DM рефереру (если не отключил категорию «refs») + запись в лог-канал."""
    if event.amount <= 0:
        return
    if event.notify_allowed:
        with suppress(TelegramAPIError):
            await bot.send_message(
                event.referrer_tg_id,
                T.notify_ref_reward.format(amount=stars(event.amount)),
            )
    if app_settings.log_channel_id is not None:
        with suppress(TelegramAPIError):
            await bot.send_message(
                app_settings.log_channel_id,
                T.log_ref_confirmed.format(
                    referrer_tg_id=event.referrer_tg_id,
                    reward=f"{event.amount:.2f}⭐",
                ),
            )

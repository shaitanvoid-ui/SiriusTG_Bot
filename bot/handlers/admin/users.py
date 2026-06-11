"""Админка: раздел «Юзеры» (Этап 9).

Поиск по tg_id / @username → карточка → бан/shadow/баланс ±.
"""

from __future__ import annotations

from contextlib import suppress

from aiogram import F, Router, html
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.filters.admin import IsAdmin
from bot.keyboards.admin_panel import kb_user_card, kb_user_search
from bot.states.admin import UserAdminStates
from db.models import User
from db.repositories.action_log import ActionLogRepo
from db.repositories.user import UserRepo
from locales.ru import T
from utils.ui import stars


router = Router(name="admin_users")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

_YES = "✅"
_NO = "—"


async def _render_card(message, session: AsyncSession, user: User) -> None:
    logs = await ActionLogRepo(session).list_recent_for_user(user.tg_id, limit=5)
    if logs:
        actions = "\n".join(
            T.admin_user_action_row.format(
                action=html.quote(l.action),
                when=l.created_at.strftime("%d.%m %H:%M") if l.created_at else "—",
            )
            for l in logs
        )
    else:
        actions = T.admin_user_actions_empty

    username_line = f"@{html.quote(user.username)}\n" if user.username else ""
    text = T.admin_user_card.format(
        tg_id=user.tg_id,
        name=html.quote(user.first_name or "—"),
        username_line=username_line,
        balance=stars(user.balance),
        debt=stars(user.debt),
        refs=user.ref_count,
        confirmed=user.confirmed_ref_count,
        streak=user.bonus_streak,
        passed=_YES if user.subs_passed_at is not None else _NO,
        banned="🚫" if user.is_banned else _NO,
        shadow="👻" if user.is_shadow_banned else _NO,
        actions=actions,
        created=user.created_at.strftime("%d.%m.%Y") if user.created_at else "—",
    )
    with suppress(Exception):
        await message.edit_text(text, reply_markup=kb_user_card(user))


async def _send_card(message: Message, session: AsyncSession, user: User) -> None:
    """То же, но новым сообщением (после текстового поиска)."""
    sent = await message.answer("…")
    await _render_card(sent, session, user)


@router.callback_query(F.data == "adm:usr")
async def cb_open(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        await callback.answer()
        return
    await state.set_state(UserAdminStates.waiting_query)
    with suppress(Exception):
        await callback.message.edit_text(T.admin_users_intro, reply_markup=kb_user_search())
    await callback.answer()


@router.message(UserAdminStates.waiting_query, F.text)
async def msg_search(message: Message, state: FSMContext, session: AsyncSession) -> None:
    query = (message.text or "").strip()
    repo = UserRepo(session)
    user: User | None = None
    if query.lstrip("-").isdigit():
        user = await repo.get_by_tg_id(int(query))
    else:
        user = await repo.get_by_username(query.lstrip("@"))
    if user is None:
        await message.answer(T.admin_user_not_found, reply_markup=kb_user_search())
        return
    await state.clear()
    await _send_card(message, session, user)


async def _resolve(callback: CallbackQuery, session: AsyncSession) -> tuple[int, User | None]:
    target_id = int((callback.data or "0").rsplit(":", 1)[-1])
    return target_id, await UserRepo(session).get_by_id(target_id)


@router.callback_query(F.data.startswith("adm:usr:ban:"))
async def cb_ban(callback: CallbackQuery, session: AsyncSession) -> None:
    target_id, user = await _resolve(callback, session)
    if user is None or callback.message is None:
        await callback.answer(T.admin_user_not_found, show_alert=True)
        return
    await UserRepo(session).set_banned(target_id, True)
    await ActionLogRepo(session).log(
        user_tg_id=user.tg_id, action="admin_ban", payload=None
    )
    await session.refresh(user)
    await _render_card(callback.message, session, user)
    await callback.answer(T.admin_user_banned_alert, show_alert=False)


@router.callback_query(F.data.startswith("adm:usr:unban:"))
async def cb_unban(callback: CallbackQuery, session: AsyncSession) -> None:
    target_id, user = await _resolve(callback, session)
    if user is None or callback.message is None:
        await callback.answer(T.admin_user_not_found, show_alert=True)
        return
    await UserRepo(session).set_banned(target_id, False)
    await ActionLogRepo(session).log(
        user_tg_id=user.tg_id, action="admin_unban", payload=None
    )
    await session.refresh(user)
    await _render_card(callback.message, session, user)
    await callback.answer(T.admin_user_unbanned_alert, show_alert=False)


@router.callback_query(F.data.startswith("adm:usr:shon:"))
async def cb_shadow_on(callback: CallbackQuery, session: AsyncSession) -> None:
    target_id, user = await _resolve(callback, session)
    if user is None or callback.message is None:
        await callback.answer(T.admin_user_not_found, show_alert=True)
        return
    await UserRepo(session).set_shadow_banned(target_id, True)
    await ActionLogRepo(session).log(
        user_tg_id=user.tg_id, action="admin_shadow_on", payload=None
    )
    await session.refresh(user)
    await _render_card(callback.message, session, user)
    await callback.answer(T.admin_user_shadow_on_alert, show_alert=False)


@router.callback_query(F.data.startswith("adm:usr:shoff:"))
async def cb_shadow_off(callback: CallbackQuery, session: AsyncSession) -> None:
    target_id, user = await _resolve(callback, session)
    if user is None or callback.message is None:
        await callback.answer(T.admin_user_not_found, show_alert=True)
        return
    await UserRepo(session).set_shadow_banned(target_id, False)
    await ActionLogRepo(session).log(
        user_tg_id=user.tg_id, action="admin_shadow_off", payload=None
    )
    await session.refresh(user)
    await _render_card(callback.message, session, user)
    await callback.answer(T.admin_user_shadow_off_alert, show_alert=False)


# ---------- баланс ± ----------

@router.callback_query(F.data.startswith("adm:usr:bal:"))
async def cb_balance(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    target_id, user = await _resolve(callback, session)
    if user is None or callback.message is None:
        await callback.answer(T.admin_user_not_found, show_alert=True)
        return
    await state.set_state(UserAdminStates.waiting_balance_delta)
    await state.update_data(target_user_id=target_id)
    with suppress(Exception):
        await callback.message.edit_text(
            T.admin_user_balance_prompt.format(tg_id=user.tg_id, balance=stars(user.balance)),
            reply_markup=kb_user_search(),
        )
    await callback.answer()


@router.message(UserAdminStates.waiting_balance_delta, F.text)
async def msg_balance_delta(message: Message, state: FSMContext, session: AsyncSession) -> None:
    raw = (message.text or "").strip().replace(",", ".")
    try:
        delta = round(float(raw), 2)
    except ValueError:
        await message.answer(T.admin_user_balance_invalid)
        return
    data = await state.get_data()
    target_id = int(data["target_user_id"])
    repo = UserRepo(session)
    user = await repo.get_by_id(target_id)
    if user is None:
        await state.clear()
        await message.answer(T.admin_user_not_found, reply_markup=kb_user_search())
        return
    if delta >= 0:
        await repo.add_balance(target_id, delta)
    else:
        await repo.subtract_with_debt(target_id, -delta)
    await ActionLogRepo(session).log(
        user_tg_id=user.tg_id, action="admin_balance_delta", payload={"delta": delta}
    )
    await state.clear()
    # add_balance/subtract_with_debt мутируют ORM-объект в памяти без flush —
    # refresh здесь экспайрил бы объект и ОТБРАСЫВАЛ начисление (баг «звёзды не прибавляются»).
    await session.flush()
    await message.answer(
        T.admin_user_balance_done.format(
            delta=f"{delta:+.2f}⭐", balance=stars(user.balance)
        )
    )
    await _send_card(message, session, user)

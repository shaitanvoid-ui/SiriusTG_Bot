"""Достижения — экран со списком и ленивым начислением наград.

При открытии экрана синхронизируем достижения: всё свежезаработанное
начисляется на баланс, новые — показываются алертом.
"""

from __future__ import annotations

from contextlib import suppress

from aiogram import F, Router, html
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.achievements import kb_achievements
from db.models import User
from db.repositories.user import UserRepo
from locales.ru import T
from services.achievements import METRIC_UNIT, AchievementsService
from services.settings import SettingsService
from utils.ui import mini_bar, stars


router = Router(name="achievements")


def _render(views) -> str:
    lines: list[str] = []
    for v in views:
        if v.unlocked:
            lines.append(
                T.ach_row_unlocked.format(
                    emoji=v.emoji, name=html.quote(v.name), reward=stars(v.reward)
                )
            )
        else:
            unit = METRIC_UNIT.get(v.metric, "")
            lines.append(
                T.ach_row_locked.format(
                    emoji=v.emoji,
                    name=html.quote(v.name),
                    bar=mini_bar(v.current, v.threshold),
                    current=v.current,
                    threshold=v.threshold,
                    unit=unit,
                    reward=stars(v.reward),
                )
            )
    unlocked = sum(1 for v in views if v.unlocked)
    return T.ach_caption.format(
        unlocked=unlocked,
        total=len(views),
        summary_bar=mini_bar(unlocked, len(views), width=10),
        rows="\n".join(lines),
    )


@router.callback_query(F.data == "ach:open")
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

    svc = AchievementsService(session, SettingsService(session))
    if not await svc.enabled():
        with suppress(Exception):
            await callback.message.edit_text(T.ach_empty, reply_markup=kb_achievements())
        await callback.answer()
        return

    awarded = await svc.sync(user)
    views = await svc.list_for_user(user)

    if not views:
        with suppress(Exception):
            await callback.message.edit_text(T.ach_empty, reply_markup=kb_achievements())
        await callback.answer()
        return

    with suppress(Exception):
        await callback.message.edit_text(_render(views), reply_markup=kb_achievements())

    if awarded:
        names = ", ".join(a.name for a in awarded)
        total = round(sum(a.reward for a in awarded), 2)
        await callback.answer(
            T.ach_unlocked_alert.format(names=names, total=stars(total)),
            show_alert=True,
        )
    else:
        await callback.answer()

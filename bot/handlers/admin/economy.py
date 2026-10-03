"""Админка: экономика — просмотр/правка settings по группам (Этап 9).

Группы строятся автоматически из префиксов ключей DEFAULTS (до точки).
Тип значения определяется по текущему значению; новые значения парсятся
в тот же тип (bool/int/float/str, dict/list — как JSON).
"""

from __future__ import annotations

import json
from contextlib import suppress
from typing import Any

from aiogram import F, Router, html
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.filters.admin import IsAdmin
from core.config import settings
from bot.keyboards.admin_panel import kb_eco_cancel, kb_eco_groups, kb_eco_keys
from bot.states.admin import EcoEditStates
from db.repositories.action_log import ActionLogRepo
from locales.ru import T
from services.settings import DEFAULTS, SettingsService
from services.settings_validation import validate_setting_change
from services.scheduler_runtime import apply_scheduler_setting


router = Router(name="admin_economy")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


def eco_groups() -> dict[str, list[str]]:
    """Группы ключей по префиксу до точки: {'click': ['click.base_reward', ...]}."""
    groups: dict[str, list[str]] = {}
    for key in DEFAULTS:
        prefix = key.split(".", 1)[0]
        groups.setdefault(prefix, []).append(key)
    return groups


def parse_value(raw: str, current: Any) -> tuple[Any, bool]:
    """Парсит raw в тип current. Возвращает (значение, ok)."""
    raw = raw.strip()
    if isinstance(current, bool):
        low = raw.lower()
        if low in ("1", "true", "yes", "on", "да"):
            return True, True
        if low in ("0", "false", "no", "off", "нет"):
            return False, True
        return None, False
    if isinstance(current, int) and not isinstance(current, bool):
        try:
            return int(raw), True
        except ValueError:
            return None, False
    if isinstance(current, float):
        try:
            return round(float(raw.replace(",", ".")), 6), True
        except ValueError:
            return None, False
    if isinstance(current, (dict, list)):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return None, False
        if not isinstance(parsed, type(current)):
            return None, False
        return parsed, True
    return raw, True  # str


def _type_name(value: Any) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, dict):
        return "json-object"
    if isinstance(value, list):
        return "json-array"
    return "str"


def _short(value: Any, limit: int = 64) -> str:
    s = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
    return html.quote(s if len(s) <= limit else s[: limit - 1] + "…")


@router.callback_query(F.data == "adm:eco")
async def cb_root(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if callback.message is None:
        await callback.answer()
        return
    with suppress(TelegramAPIError):
        await callback.message.edit_text(
            T.admin_eco_root, reply_markup=kb_eco_groups(sorted(eco_groups()))
        )
    await callback.answer()


@router.callback_query(F.data.startswith("adm:eco:g:"))
async def cb_group(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    if callback.data is None or callback.message is None:
        await callback.answer()
        return
    group = callback.data.rsplit(":", 1)[-1]
    keys = eco_groups().get(group, [])
    if not keys:
        await callback.answer()
        return
    svc = SettingsService(session)
    rows = []
    for k in keys:
        value = await svc.get(k, DEFAULTS[k][0])
        rows.append(T.admin_eco_row.format(key=k, value=_short(value)))
    text = T.admin_eco_group.format(group=group, rows="\n".join(rows))
    with suppress(TelegramAPIError):
        await callback.message.edit_text(text, reply_markup=kb_eco_keys(group, keys))
    await callback.answer()


@router.callback_query(F.data.startswith("adm:eco:k:"))
async def cb_key(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    if callback.data is None or callback.message is None:
        await callback.answer()
        return
    key = callback.data.split("adm:eco:k:", 1)[-1]
    if key not in DEFAULTS:
        await callback.answer()
        return
    if key.startswith(("gifts.", "antifraud.")) and callback.from_user.id != settings.owner_id:
        await callback.answer(T.admin_gift_owner_only, show_alert=True)
        return
    svc = SettingsService(session)
    value = await svc.get(key, DEFAULTS[key][0])
    group = key.split(".", 1)[0]
    await state.set_state(EcoEditStates.waiting_value)
    await state.update_data(eco_key=key)
    with suppress(TelegramAPIError):
        await callback.message.edit_text(
            T.admin_eco_edit_prompt.format(
                key=key,
                description=html.quote(DEFAULTS[key][1]),
                value=_short(value, limit=512),
                type=_type_name(value),
            ),
            reply_markup=kb_eco_cancel(group),
        )
    await callback.answer()


@router.message(EcoEditStates.waiting_value, F.text)
async def msg_value(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    scheduler: AsyncIOScheduler | None = None,
) -> None:
    data = await state.get_data()
    key = data.get("eco_key", "")
    if key not in DEFAULTS:
        await state.clear()
        return
    if key.startswith(("gifts.", "antifraud.")) and (message.from_user is None or message.from_user.id != settings.owner_id):
        await state.clear()
        await message.answer(T.admin_gift_owner_only)
        return
    svc = SettingsService(session)
    current = await svc.get(key, DEFAULTS[key][0])
    new_value, ok = parse_value(message.text or "", current)
    if not ok:
        await message.answer(T.admin_eco_invalid.format(type=_type_name(current)))
        return
    validation_error = await validate_setting_change(key, new_value, svc)
    if validation_error:
        await message.answer(
            T.admin_eco_validation_error.format(error=html.quote(validation_error))
        )
        return
    await svc.set(key, new_value, DEFAULTS[key][1])
    apply_scheduler_setting(scheduler, key, new_value)
    await ActionLogRepo(session).log(
        user_tg_id=message.from_user.id if message.from_user else None,
        action="admin_setting_changed",
        payload={"key": key, "value": new_value},
    )
    await state.clear()
    group = key.split(".", 1)[0]
    keys = eco_groups().get(group, [])
    await message.answer(
        T.admin_eco_saved.format(key=key, value=_short(new_value)),
        reply_markup=kb_eco_keys(group, keys),
    )

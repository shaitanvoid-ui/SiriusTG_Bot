from __future__ import annotations

import re
from contextlib import suppress

from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.flow import notify_referrer_reward, route_user
from core.logger import get_logger
from db.models import User
from db.repositories.action_log import ActionLogRepo
from db.repositories.referral import ReferralRepo
from services.partner import PartnerService
from services.referral import ReferralService
from services.settings import SettingsService


router = Router(name="start")
log = get_logger(__name__)


_REF_PAYLOAD_RE = re.compile(r"^r(\d{1,20})$")
_PARTNER_PAYLOAD_RE = re.compile(r"^p([a-z0-9]{4,16})$")


def _parse_referrer_tg_id(arg: str | None) -> int | None:
    if not arg:
        return None
    m = _REF_PAYLOAD_RE.match(arg.strip())
    if m is None:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def _parse_partner_code(arg: str | None) -> str | None:
    if not arg:
        return None
    m = _PARTNER_PAYLOAD_RE.match(arg.strip())
    return m.group(1) if m else None


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    command: CommandObject,
    state: FSMContext,
    session: AsyncSession,
    db_user: User | None = None,
) -> None:
    if message.from_user is None or db_user is None:
        return
    await state.clear()

    referrer_tg_id = _parse_referrer_tg_id(command.args if command else None)
    await ActionLogRepo(session).log(
        user_tg_id=message.from_user.id,
        action="start",
        payload={
            "username": message.from_user.username,
            "ref_payload": command.args if command else None,
        },
    )

    settings_svc = SettingsService(session)
    ref_svc = ReferralService(session, settings_svc)

    if referrer_tg_id is not None:
        await ref_svc.try_attach_referrer(user=db_user, referrer_tg_id=referrer_tg_id)

    partner_code = _parse_partner_code(command.args if command else None)
    if partner_code is not None:
        await PartnerService(session, settings_svc).track_start(db_user, partner_code)

    # self-heal: юзер уже passed гейт, но его реф не подтверждён → дотягиваем награду
    healed_event = None
    if db_user.subs_passed_at is not None:
        existing = await ReferralRepo(session).get_by_referred(db_user.id)
        if existing is not None and not existing.is_confirmed:
            healed_event = await ref_svc.on_user_passed_subs(user=db_user)

    await route_user(message=message, state=state, session=session, user=db_user)

    if healed_event is not None and message.bot is not None:
        with suppress(TelegramAPIError):
            await notify_referrer_reward(message.bot, healed_event)

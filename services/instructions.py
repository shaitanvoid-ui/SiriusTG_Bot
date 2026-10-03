"""Native instructions; upgrade only unmodified, known default pages."""
from __future__ import annotations

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Instruction
from db.repositories.instruction import InstructionRepo
from db.repositories.setting import SettingRepo


DEFAULT_INSTRUCTIONS = [
    (
        "Награды и мой день",
        "<b>Выбери доступное действие</b>\n\n"
        "В «Мой день» видно, какие награды доступны сейчас. Все способы собраны в «Награды»: "
        "бонус дня, кликер, задания, колесо и приглашения друзей. Промокоды доступны в профиле.\n\n"
        "Сумма и условия показаны до получения. Задание начисляется после проверки подписки; "
        "приглашение — после обязательных проверок друга.\n\n"
        "<i>Начисления учитываются во внутренних единицах SIRIUS. Они не пополняют твой Stars-баланс Telegram.</i>",
        1,
    ),
    (
        "Счёт и подарки",
        "<b>Доступно, в резерве и долг</b>\n\n"
        "В профиле показаны доступные единицы, резерв подарков и долг. История счёта содержит начисления "
        "и списания, кроме отдельных нажатий кликера. При нарушении условий награда может быть списана; "
        "при нехватке средств появится долг. Следующие начисления сначала погасят его.\n\n"
        "<b>Как получить подарок</b>\n\n"
        "Открой «Подарки», выбери обычный подарок Telegram и проверь стоимость, число друзей и дневной лимит. "
        "После подтверждения сумма из счёта SIRIUS резервируется. Настоящие Stars для оплаты находятся на аккаунте отправителя.\n\n"
        "До начала отправки заявку можно отменить. При неизвестном результате резерв сохраняется до сверки; "
        "повторная покупка и возврат не запускаются. Срок выдачи зависит от доступности подарка и условий отправки.\n\n"
        "<i>Точный статус и доступные действия — в «Мои заявки». Начисление единиц в боте не означает получение Stars на аккаунт.</i>",
        2,
    ),
    (
        "Команда, уровни и рейтинг",
        "<b>Приглашай по своей ссылке</b>\n\n"
        "Ссылка и готовое приглашение — в «Моя команда». Награда начисляется после обязательных проверок друга. "
        "Срок закрепления и лимит приглашений показаны в этом разделе. Если друг отпишется раньше, награда спишется.\n\n"
        "Подтверждённые друзья повышают уровень и дневной лимит кликера. Прогресс до следующего уровня виден в профиле.\n\n"
        "<b>Рейтинг</b>\n\n"
        "Сравнивает подтверждённых друзей за выбранный период. Условия участия и награды показаны в рейтинге; "
        "награды начисляются на внутренний счёт.",
        3,
    ),
    (
        "Бонус дня и серия",
        "<b>Получай бонус каждый день</b>\n\n"
        "Бонус доступен раз в сутки по московскому времени. Сумма растёт вместе с серией; "
        "текущая награда и следующие ступени показаны в карточке. Пропуск дня сбрасывает серию.\n\n"
        "Если в карточке есть условие для профиля, добавь личную ссылку в Telegram → Изменить профиль → О себе. "
        "Она должна оставаться в профиле. Затем нажми «Забрать награду».\n\n"
        "При недоступной проверке попытка не расходуется. Уже полученный бонус показан отдельным статусом; "
        "новые сутки начинаются в 00:00 МСК.",
        4,
    ),
]

_CONTENT_VERSION = 3
_VERSION_KEY = "system.instructions_content_version"
# Exact title + body + sort_order fingerprints of v1 (833a1f8) and v2 defaults.
# Matching a title alone must never overwrite an owner's edited body or order.
_KNOWN_DEFAULT_FINGERPRINTS = frozenset({
    "5129dcad12fedede81a1fbc90c4aec102254f396a20561408ffff4f0c485c55a",
    "53ab30a306cc5396a29f4a88add60bf57b1431ee042ebd11966ea0d966e6e264",
    "8ed3540073964bb6a0befe368cc1ad2b1570b613dca85279e77fcb7adc415539",
    "9b9c022089bc7faa6ba3b2c8d087cff3aceecc8b3eaa91001828b1503f05cf12",
    "a83bd50150f8292a168702e8744efe0cd4db2a684fd97ceccf1755fb234f01c4",
    "a8927f0d85c68283d5486d0dd1d06181db28f3fe2a8ef78cbf6de4e8de3e85c7",
    "c5514b2fae99030f3300b5503221e5e98d063bddb4ee864f049606f5e1480ca2",
    "ca26f2a9a807e6036c675ed05b9bd93407424f17ed4ff0deb66e666a46d7875a",
})


def _fingerprint(title: str, body: str, sort_order: int) -> str:
    content = json.dumps((title, body, sort_order), ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


async def seed_instructions(session: AsyncSession) -> None:
    """Seed once; upgrade each known, unmodified page without replacing custom content."""
    repo = InstructionRepo(session)
    setting_repo = SettingRepo(session)
    version = await setting_repo.get(_VERSION_KEY, 0)
    try:
        current_version = int(version)
    except (TypeError, ValueError):
        current_version = 0
    if current_version >= _CONTENT_VERSION:
        return

    pages = await repo.get_active()
    if not pages:
        # Deleted custom pages also represent an owner's choice. Do not restore
        # defaults over an inactive set or duplicate them on the next restart.
        existing_id = await session.scalar(select(Instruction.id).limit(1))
        if existing_id is None:
            for title, body, sort_order in DEFAULT_INSTRUCTIONS:
                await repo.create(title, body, sort_order)
    else:
        defaults = {order: (title, body) for title, body, order in DEFAULT_INSTRUCTIONS}
        for page in pages:
            if _fingerprint(page.title, page.body, page.sort_order) in _KNOWN_DEFAULT_FINGERPRINTS:
                title, body = defaults[page.sort_order]
                await repo.update(page.id, title, body)

    await setting_repo.set(_VERSION_KEY, _CONTENT_VERSION, "Версия системной инструкции")

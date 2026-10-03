"""Сервис инструкций."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from db.repositories.instruction import InstructionRepo
from db.repositories.setting import SettingRepo
from db.models import Instruction


DEFAULT_INSTRUCTIONS = [
    (
        "Как заработать ⭐",
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "Все доступные способы собраны в разделе «💎 Заработать»:\n\n"
        "▸ <b>👥 Рефералы</b> — приглашай друзей по личной ссылке\n"
        "▸ <b>👆 Кликер</b> — получай звёзды за тапы в пределах лимита\n"
        "▸ <b>🎁 Ежедневный бонус</b> — поддерживай стрик\n"
        "▸ <b>🎯 Задания</b> — выполняй условия спонсоров\n"
        "▸ <b>🎡 Колесо</b> — используй доступные вращения\n"
        "▸ <b>🎟 Промокоды</b> — активируй коды проекта\n\n"
        "<i>Точные награды и лимиты всегда показаны на экране до действия.</i>",
        1,
    ),
    (
        "Баланс и история",
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "▸ Текущий баланс всегда виден в главном меню и профиле.\n"
        "▸ Начисления и списания собраны в разделе «История».\n"
        "▸ Если условие награды перестало выполняться, начисление может быть отменено.\n"
        "▸ При нехватке баланса отменённая награда учитывается как долг.\n\n"
        "<i>Функции, которых нет в текущем меню, пока недоступны.</i>",
        2,
    ),
    (
        "Уровни и топ",
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "<b>Уровни</b> растут с подтверждёнными рефералами:\n"
        "🥉 Бронза → 🥈 Серебро → 🥇 Золото → 💠 Платина → 💎 Алмаз\n\n"
        "Каждый уровень увеличивает дневной лимит кликера.\n\n"
        "<b>Топ</b> — рейтинг по рефералам за выбранный период.\n"
        "Условия попадания и награды, если они включены, показаны в самом разделе.",
        3,
    ),
    (
        "Ежедневный бонус и стрик",
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "<b>Бонус</b> можно получить раз в сутки. Награда растёт вместе со стриком.\n\n"
        "Если на экране бонуса показано условие, добавь личную реферальную ссылку "
        "в поле Telegram «О себе».\n\n"
        "Пропуск дня сбрасывает стрик. Актуальная лестница наград всегда видна "
        "в карточке бонуса.",
        4,
    ),
]

_CONTENT_VERSION = 2
_VERSION_KEY = "system.instructions_content_version"
_LEGACY_DEFAULT_TITLES = {
    1: "Как заработать ⭐",
    2: "Как вывести ⭐ в подарки",
    3: "Уровни и топ",
    4: "Ежедневный бонус и стрик",
}


async def seed_instructions(session: AsyncSession) -> None:
    """Засеять инструкции и один раз обновить только узнаваемый legacy-набор."""
    repo = InstructionRepo(session)
    setting_repo = SettingRepo(session)
    version = await setting_repo.get(_VERSION_KEY, 0)
    pages = await repo.get_active()
    if not pages:
        for title, body, sort_order in DEFAULT_INSTRUCTIONS:
            await repo.create(title, body, sort_order)
        await setting_repo.set(_VERSION_KEY, _CONTENT_VERSION, "Версия системной инструкции")
        return

    try:
        current_version = int(version)
    except (TypeError, ValueError):
        current_version = 0
    if current_version >= _CONTENT_VERSION:
        return

    by_order = {page.sort_order: page for page in pages}
    looks_like_legacy = len(pages) == len(_LEGACY_DEFAULT_TITLES) and all(
        order in by_order and by_order[order].title == title
        for order, title in _LEGACY_DEFAULT_TITLES.items()
    )
    if looks_like_legacy:
        for title, body, sort_order in DEFAULT_INSTRUCTIONS:
            page = by_order[sort_order]
            await repo.update(page.id, title, body)

    # Пользовательские страницы не перезаписываем; версию всё равно фиксируем,
    # чтобы не повторять эвристику на каждом старте.
    await setting_repo.set(_VERSION_KEY, _CONTENT_VERSION, "Версия системной инструкции")

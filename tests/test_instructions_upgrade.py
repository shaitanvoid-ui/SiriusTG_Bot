"""Instruction upgrades preserve owner's text, order and deleted pages."""
from __future__ import annotations

from sqlalchemy import func, select

from db.models import Instruction
from db.repositories.instruction import InstructionRepo
from db.repositories.setting import SettingRepo
from services.instructions import DEFAULT_INSTRUCTIONS, seed_instructions


_V2_PAGES = [('Как заработать ⭐', '━━━━━━━━━━━━━━━━━━━\n\nВсе доступные способы собраны в разделе «💎 Заработать»:\n\n▸ <b>👥 Рефералы</b> — приглашай друзей по личной ссылке\n▸ <b>👆 Кликер</b> — получай звёзды за тапы в пределах лимита\n▸ <b>🎁 Ежедневный бонус</b> — поддерживай стрик\n▸ <b>🎯 Задания</b> — выполняй условия спонсоров\n▸ <b>🎡 Колесо</b> — используй доступные вращения\n▸ <b>🎟 Промокоды</b> — активируй коды проекта\n\n<i>Точные награды и лимиты всегда показаны на экране до действия.</i>', 1), ('Баланс и история', '━━━━━━━━━━━━━━━━━━━\n\n▸ Текущий баланс всегда виден в главном меню и профиле.\n▸ Начисления и списания собраны в разделе «История».\n▸ Если условие награды перестало выполняться, начисление может быть отменено.\n▸ При нехватке баланса отменённая награда учитывается как долг.\n\n<i>Функции, которых нет в текущем меню, пока недоступны.</i>', 2), ('Уровни и топ', '━━━━━━━━━━━━━━━━━━━\n\n<b>Уровни</b> растут с подтверждёнными рефералами:\n🥉 Бронза → 🥈 Серебро → 🥇 Золото → 💠 Платина → 💎 Алмаз\n\nКаждый уровень увеличивает дневной лимит кликера.\n\n<b>Топ</b> — рейтинг по рефералам за выбранный период.\nУсловия попадания и награды, если они включены, показаны в самом разделе.', 3), ('Ежедневный бонус и стрик', '━━━━━━━━━━━━━━━━━━━\n\n<b>Бонус</b> можно получить раз в сутки. Награда растёт вместе со стриком.\n\nЕсли на экране бонуса показано условие, добавь личную реферальную ссылку в поле Telegram «О себе».\n\nПропуск дня сбрасывает стрик. Актуальная лестница наград всегда видна в карточке бонуса.', 4)]
_V1_PAGES = [('Как заработать ⭐', '━━━━━━━━━━━━━━━━━━━\n\nЕсть несколько способов:\n\n▸ <b>👥 Рефералы</b> — зови друзей, получай 3⭐ за каждого\n▸ <b>👆 Кликер</b> — тапай и копи звёзды (до 10⭐/день)\n▸ <b>🎁 Ежедневный бонус</b> — заходи каждый день\n▸ <b>🎯 Задания</b> — подписывайся на каналы\n▸ <b>🎡 Колесо фортуны</b> — крути бесплатно раз в сутки\n▸ <b>🎟 Промокоды</b> — вводи коды из нашего канала', 1), ('Как вывести ⭐ в подарки', '━━━━━━━━━━━━━━━━━━━\n\n1. Накопи <b>15⭐</b> и более\n2. Подтверди не менее <b>5 рефералов</b>\n3. Открой раздел «💸 Вывод подарков»\n4. Выбери подарок из витрины\n5. Подарочная⭐ поступят тебе в Telegram\n\n<i>Ограничение: до 5 выводов в сутки.</i>', 2), ('Уровни и топ', '━━━━━━━━━━━━━━━━━━━\n\n<b>Уровни</b> растут с подтверждёнными рефералами:\n🥉 Бронза → 🥈 Серебро → 🥇 Золото → 💠 Платина → 💎 Алмаз\n\nКаждый уровень увеличивает дневной лимит кликера.\n\n<b>Топ-100</b> — рейтинг по рефералам.\nТоп-10 недели получают награды ⭐.\nМинимум 10 подтверждённых рефералов для попадания.', 3), ('Ежедневный бонус и стрик', '━━━━━━━━━━━━━━━━━━━\n\n<b>Бонус</b> начисляется раз в сутки. Размер зависит от стрика:\n• 1 день — 0.5⭐\n• 3 дня — 0.7⭐\n• 7 дней — 1.0⭐\n• 14 дней — 1.5⭐\n• 30+ дней — 2.0⭐\n\nУсловие: в bio должна стоять твоя реф-ссылка.\nПропуск дня — стрик сбрасывается.', 4)]
_VERSION_KEY = "system.instructions_content_version"


async def _seed_old(session, pages, version=2):
    repo = InstructionRepo(session)
    result = [await repo.create(title, body, order) for title, body, order in pages]
    await SettingRepo(session).set(_VERSION_KEY, version)
    return result


async def test_exact_v2_defaults_upgrade_to_v3_once(session):
    old_pages = await _seed_old(session, _V2_PAGES)
    old_ids = [page.id for page in old_pages]
    await seed_instructions(session)
    pages = await InstructionRepo(session).get_active()
    assert [(p.title, p.body, p.sort_order) for p in pages] == DEFAULT_INSTRUCTIONS
    assert [p.id for p in pages] == old_ids
    assert await SettingRepo(session).get(_VERSION_KEY) == 3
    await seed_instructions(session)
    assert await session.scalar(select(func.count()).select_from(Instruction)) == 4


async def test_exact_v1_defaults_upgrade_to_v3(session):
    await _seed_old(session, _V1_PAGES, version=0)
    await seed_instructions(session)
    pages = await InstructionRepo(session).get_active()
    assert [(p.title, p.body, p.sort_order) for p in pages] == DEFAULT_INSTRUCTIONS


async def test_same_default_title_with_custom_body_is_preserved(session):
    edited = list(_V2_PAGES)
    title, _, order = edited[1]
    edited[1] = (title, "Условия владельца: не заменять этот текст.", order)
    originals = await _seed_old(session, edited)
    custom_id = originals[1].id
    await seed_instructions(session)
    pages = await InstructionRepo(session).get_active()
    custom = next(p for p in pages if p.id == custom_id)
    assert (custom.title, custom.body, custom.sort_order) == edited[1]
    assert [(p.title, p.body, p.sort_order) for p in pages if p.id != custom_id] == [p for p in DEFAULT_INSTRUCTIONS if p[2] != order]
    await seed_instructions(session)
    assert await session.scalar(select(func.count()).select_from(Instruction)) == 4


async def test_default_body_with_changed_order_is_preserved(session):
    title, body, _ = _V2_PAGES[0]
    await _seed_old(session, [(title, body, 99)])
    await seed_instructions(session)
    page = (await InstructionRepo(session).get_active())[0]
    assert (page.title, page.body, page.sort_order) == (title, body, 99)


async def test_custom_instruction_set_is_preserved(session):
    repo = InstructionRepo(session)
    custom = await repo.create("Моя страница", "Мой текст", 1)
    await seed_instructions(session)
    await session.refresh(custom)
    assert custom.title == "Моя страница"
    assert custom.body == "Мой текст"
    assert await repo.count() == 1


async def test_deleted_custom_pages_are_not_reseeded(session):
    repo = InstructionRepo(session)
    custom = await repo.create("Моя страница", "Мой текст", 1)
    await repo.delete(custom.id)
    await seed_instructions(session)
    await seed_instructions(session)
    assert await repo.count() == 0
    assert await session.scalar(select(func.count()).select_from(Instruction)) == 1
    await session.refresh(custom)
    assert custom.body == "Мой текст" and custom.is_active is False


async def test_empty_database_seeds_v3_once(session):
    await seed_instructions(session)
    await seed_instructions(session)
    pages = await InstructionRepo(session).get_active()
    assert [(p.title, p.body, p.sort_order) for p in pages] == DEFAULT_INSTRUCTIONS
    assert await SettingRepo(session).get(_VERSION_KEY) == 3

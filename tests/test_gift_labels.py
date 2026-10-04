"""Gift appearance comes from sticker metadata, never price or callback identity."""

from types import SimpleNamespace

import pytest
from telethon.tl import types

from bot.keyboards.gifts import kb_catalogue, kb_gift_history, kb_gift_notification
from userbot.gifts import _ordinary_gift
from utils.gift_labels import gift_label


@pytest.mark.parametrize("emoji,expected", [
    ("💝", "💝 Сердце с лентой"), ("🧸", "🧸 Мишка"),
    ("🎁", "🎁 Подарочная коробка"), ("💍", "💍 Кольцо"),
])
def test_sticker_alt_identifies_untitled_ordinary_gift(emoji, expected):
    sticker = SimpleNamespace(attributes=[types.DocumentAttributeSticker(emoji, types.InputStickerSetEmpty())])
    raw = types.StarGift(id=77, sticker=sticker, stars=15, convert_stars=12)
    gift = _ordinary_gift(raw)
    assert gift.title == expected
    assert (gift.id, gift.stars, gift.kind, gift.available) == (77, 15, "ordinary", True)


def test_custom_emoji_alt_takes_precedence_over_opaque_title():
    sticker = SimpleNamespace(attributes=[types.DocumentAttributeCustomEmoji("🧸", types.InputStickerSetEmpty())])
    raw = types.StarGift(id=88, title="Internal gift title", sticker=sticker, stars=25, convert_stars=20)
    assert _ordinary_gift(raw).title == "🧸 Мишка"


@pytest.mark.parametrize("title,expected", [
    ("Teddy Bear", "🧸 Мишка"), ("Diamond Ring", "💍 Кольцо"),
    ("Подарок #77", "🎁 Подарок Telegram"), (None, "🎁 Подарок Telegram"),
    ("<New & unusual gift>", "🎁 <New & unusual gift>"),
    ("💝 Сердце с лентой", "💝 Сердце с лентой"),
])
def test_persisted_titles_have_readable_idempotent_fallback(title, expected):
    assert gift_label(title) == expected
    assert gift_label(expected) == expected


def test_same_appearance_and_price_keep_distinct_gift_and_request_ids():
    gifts = [SimpleNamespace(id=id, title="Teddy Bear", stars=15) for id in (7, 8)]
    markup = kb_catalogue(gifts)
    assert [row[0].callback_data for row in markup.inline_keyboard[:2]] == ["gift:view:7", "gift:view:8"]
    assert all(row[0].text == "🧸 Мишка · 15 ед." for row in markup.inline_keyboard[:2])
    history = kb_gift_history([SimpleNamespace(id=42, title="Diamond Ring")])
    assert history.inline_keyboard[0][0].text == "💍 Кольцо · #42"
    assert history.inline_keyboard[0][0].callback_data == "gift:request:42"
    assert kb_gift_notification(42).inline_keyboard[0][0].callback_data == "gift:request:42"

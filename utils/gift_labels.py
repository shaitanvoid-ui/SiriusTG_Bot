"""Readable ordinary gift labels from Telegram's sticker metadata.

Never identify a gift by price: different gifts can cost the same amount.
The real gift ID continues to drive every quote and payment.
"""

from __future__ import annotations

import re


# The sticker's associated emoji identifies the ordinary gift's appearance.
_NAMES = {
    "💝": "Сердце с лентой", "❤": "Сердце", "💖": "Сердце",
    "🧸": "Мишка", "🎁": "Подарочная коробка", "💍": "Кольцо",
    "🌹": "Роза", "💐": "Букет", "🌷": "Тюльпан",
    "🎂": "Торт", "🍰": "Торт", "🍾": "Шампанское",
    "🚀": "Ракета", "🏆": "Кубок",
}
_ALIASES = {
    "heart": "❤", "red heart": "❤", "сердце": "❤", "красное сердце": "❤",
    "heart with ribbon": "💝", "сердце с лентой": "💝",
    "teddy bear": "🧸", "teddybear": "🧸", "bear": "🧸", "мишка": "🧸",
    "gift": "🎁", "gift box": "🎁", "подарочная коробка": "🎁",
    "ring": "💍", "diamond ring": "💍", "кольцо": "💍",
    "rose": "🌹", "роза": "🌹", "bouquet": "💐", "букет": "💐",
    "tulip": "🌷", "тюльпан": "🌷", "cake": "🎂", "торт": "🎂",
    "champagne": "🍾", "шампанское": "🍾", "rocket": "🚀", "ракета": "🚀",
    "trophy": "🏆", "кубок": "🏆",
}


def _key(value: str) -> str:
    return value.replace("\ufe0f", "").strip()


def gift_label(title: str | None, emoji: str | None = None) -> str:
    """A plain-text label, also safe for older persisted request titles.

HTML escaping belongs to the message renderer, not the label. Unknown genuine
titles are retained rather than assigning a misleading familiar gift name.
"""
    title = " ".join((title or "").split())
    if emoji and _key(emoji) in _NAMES:
        symbol = _key(emoji)
        return f"{'❤️' if symbol == '❤' else symbol} {_NAMES[symbol]}"
    for symbol in _NAMES:
        if title.startswith(symbol):
            return title
    symbol = _ALIASES.get(title.casefold())
    if symbol:
        return gift_label(None, symbol)
    if not title or re.fullmatch(r"Подарок\s*#\d+", title):
        title = "Подарок Telegram"
    return f"🎁 {title}"


def ordinary_gift_label(raw: object) -> str:
    """Read sticker alt metadata without network requests or custom emoji fees."""
    sticker = getattr(raw, "sticker", None)
    for attribute in getattr(sticker, "attributes", ()):
        # These are the two MTProto document attributes carrying an emoji alt.
        if type(attribute).__name__ in {"DocumentAttributeSticker", "DocumentAttributeCustomEmoji"}:
            emoji = getattr(attribute, "alt", "")
            if _key(emoji) in _NAMES:
                return gift_label(getattr(raw, "title", None), emoji)
    return gift_label(getattr(raw, "title", None))

"""Native card structure, honest amounts and mobile keyboard presentation."""
from __future__ import annotations

from html.parser import HTMLParser
from string import Formatter

from bot.handlers.gifts import render_gift
from locales.ru import T
from scripts.ui_preview import build_screens
from utils.rich import is_card, render_rich_html
from utils.ui import stars


class RichStructure(HTMLParser):
    """Check nesting explicitly; browser error recovery would hide malformed cards."""

    block_tags = {"p", "table", "details", "pre", "blockquote", "footer", "h2", "h3", "ul", "ol"}
    allowed = block_tags | {"b", "i", "u", "s", "a", "code", "br", "tr", "td", "summary", "li", "tg-time", "tg-spoiler"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        assert tag in self.allowed, f"Unexpected native tag: {tag}"
        assert not (tag in self.block_tags and "p" in self.stack), f"Block {tag} nested inside paragraph"
        if tag != "br":
            self.stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        assert self.stack and self.stack[-1] == tag, f"Unbalanced {tag}: {self.stack}"
        self.stack.pop()


def _validate_rich(html: str) -> None:
    parser = RichStructure()
    parser.feed(html)
    parser.close()
    assert parser.stack == []
    assert "__sirius_block_" not in html


def test_all_locale_cards_render_without_malformed_native_blocks() -> None:
    formatter = Formatter()
    for key, template in vars(T).items():
        if not isinstance(template, str) or not is_card(template):
            continue
        # Numeric dummy fields also support existing .2f amount format specs.
        fields = {name: 7 for _, name, _, _ in formatter.parse(template) if name}
        try:
            _validate_rich(render_rich_html(template.format(**fields)))
        except AssertionError as error:
            raise AssertionError(f"Locale card {key}: {error}") from error


def test_preview_real_renderers_keep_blocks_separate_and_ornaments_out() -> None:
    for label, text, _ in build_screens():
        rich = render_rich_html(text)
        try:
            _validate_rich(rich)
        except AssertionError as error:
            raise AssertionError(f"Preview {label}: {error}") from error
        assert "<h2>" in rich, label
        assert not any(glyph in rich for glyph in ("━", "─", "╭", "│", "╰")), label


def test_profile_available_and_reserved_amounts_are_readable_separately() -> None:
    profile = next(text for label, text, _ in build_screens() if label.startswith("Профиль"))
    assert f"<b>{stars(28.4)}</b>" in profile
    assert f"<b>{stars(15)}</b>\n\n" in profile
    assert "В резерве" in profile
    assert "не пополняют Stars-баланс Telegram" in profile
    assert "⭐" not in profile


def test_gift_card_distinguishes_internal_cost_from_telegram_price() -> None:
    text = next(text for label, text, _ in build_screens() if label.startswith("Подарок"))
    assert "Из счёта SIRIUS" in text and "15 ед." in text
    assert "Цена Telegram" in text and "15 Stars" in text
    assert "обычные подарки Telegram" in text
    assert "Конвертация" not in text and "перепродажа" not in text


def test_gift_dynamic_title_stays_text_in_rich_document() -> None:
    from types import SimpleNamespace

    gift = SimpleNamespace(title='Сердце & <img src="x">', stars=15, available=True,
        kind="ordinary", reason=None, requires_premium=False, limited=False)
    rich = render_rich_html(render_gift(gift))
    _validate_rich(rich)
    assert "&lt;img" in rich and "<img" not in rich


def test_preview_keyboards_fit_mobile_rows_and_have_concrete_actions() -> None:
    for label, _, markup in build_screens():
        for row in markup.inline_keyboard:
            assert len(row) <= 2, label
            for button in row:
                assert button.text and len(button.text) <= 48, label
                if button.disabled is not None:
                    assert button.callback_data is None and button.style is None, label
                else:
                    assert button.callback_data or button.url or button.copy_text, label
                if button.callback_data:
                    assert len(button.callback_data.encode("utf-8")) <= 64, label

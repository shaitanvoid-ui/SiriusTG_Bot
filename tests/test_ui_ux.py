"""Регрессии единой SIRIUS Elite UI-системы и иерархической навигации."""

from __future__ import annotations

from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

from bot.handlers.admin.economy import eco_groups
from bot.keyboards.admin_panel import kb_user_card
from bot.keyboards.bonus import kb_bonus
from bot.keyboards.clicker import kb_clicker
from bot.keyboards.instructions import kb_instruction_page
from bot.keyboards.main_menu import kb_main_menu
from bot.keyboards.reviews import kb_review_rating
from bot.keyboards.support import kb_faq_list, kb_support_close_confirm
from bot.keyboards.wheel import kb_wheel
from locales.ru import T
from services.instructions import DEFAULT_INSTRUCTIONS
from services.settings import DEFAULTS
from utils.links import build_share_url
from utils.ui import BUTTON_TEXT_LIMIT, button_text, count_ru, html_text, plural_ru


def _callbacks(markup) -> list[str]:
    return [
        button.callback_data
        for row in markup.inline_keyboard
        for button in row
        if button.callback_data
    ]


def _texts(markup) -> list[str]:
    return [button.text for row in markup.inline_keyboard for button in row]


def test_ui_helpers_escape_clip_and_decline_in_russian() -> None:
    assert html_text('<user id="1">&') == "&lt;user id=&quot;1&quot;&gt;&amp;"
    assert plural_ru(1, "день", "дня", "дней") == "день"
    assert plural_ru(2, "день", "дня", "дней") == "дня"
    assert plural_ru(11, "день", "дня", "дней") == "дней"
    assert plural_ru(22, "день", "дня", "дней") == "дня"
    assert count_ru(25, "реферал", "реферала", "рефералов") == "25 рефералов"
    assert len(button_text("  очень   длинная подпись " * 10)) <= BUTTON_TEXT_LIMIT


def test_main_menu_does_not_advertise_unfinished_withdrawal() -> None:
    markup = kb_main_menu(channel_url="https://t.me/sirius")
    callbacks = _callbacks(markup)
    assert "feat:soon:withdraw" not in callbacks
    assert all("вывод" not in text.lower() for text in _texts(markup))


def test_unfinished_withdrawal_is_absent_from_live_help_defaults() -> None:
    content = "\n".join(title + "\n" + body for title, body, _ in DEFAULT_INSTRUCTIONS)
    faq = DEFAULTS["support.faq"][0]
    content += "\n" + "\n".join(str(item) for item in faq)
    lowered = content.lower()
    assert "вывод подарков" not in lowered
    assert "как вывести" not in lowered


def test_wheel_respects_paid_spin_affordability() -> None:
    locked = kb_wheel(free_available=False, can_pay=False, cost=5)
    assert any(button.disabled is not None for row in locked.inline_keyboard for button in row)
    assert "whl:spin:paid" not in _callbacks(locked)
    assert T.btn_wheel_locked in _texts(locked)

    available = kb_wheel(free_available=False, can_pay=True, cost=5)
    assert "whl:confirm" in _callbacks(available)
    assert "whl:noop" not in _callbacks(available)


def test_child_sections_return_to_their_parent_hub() -> None:
    assert "sec:earn" in _callbacks(kb_clicker(can_click=True))
    assert "sec:earn" in _callbacks(kb_bonus(can_claim=True))
    assert "sec:earn" in _callbacks(
        kb_wheel(free_available=True, can_pay=True, cost=1)
    )
    assert "sec:help" in _callbacks(kb_instruction_page(page_idx=0, total=2))


def test_faq_always_offers_a_real_support_question() -> None:
    assert "sup:new" in _callbacks(kb_faq_list([]))
    assert "sup:new" in _callbacks(kb_faq_list(["Как получить награду?"]))


def test_support_close_requires_confirmation() -> None:
    callbacks = _callbacks(kb_support_close_confirm(42))
    assert callbacks == ["sup:t:close_yes:42", "sup:t:42"]


def test_review_rating_has_one_selected_value_and_mobile_rows() -> None:
    markup = kb_review_rating(3)
    labels = _texts(markup)
    assert sum(label.startswith("●") for label in labels) == 1
    assert any(label.startswith("● 3") for label in labels)
    assert [len(row) for row in markup.inline_keyboard[:2]] == [3, 2]


def test_referral_share_url_contains_invite_only_once() -> None:
    invite = "https://t.me/sirius_bot?start=r42"
    share = build_share_url(invite, T.ref_share_text)
    query = parse_qs(urlparse(share).query)
    assert query["url"] == [invite]
    assert invite not in query["text"][0]


def test_stage12_shadow_controls_are_not_exposed_in_admin_ui() -> None:
    user = SimpleNamespace(id=7, is_banned=False, is_shadow_banned=False)
    callbacks = _callbacks(kb_user_card(user))
    assert not any(":shon:" in callback or ":shoff:" in callback for callback in callbacks)
    assert all("shadow" not in page.lower() for page in T.terms_pages_bodies)


def test_gift_admission_and_sender_settings_are_available_in_economy_ui() -> None:
    assert "withdraw" in eco_groups() and "gifts" in eco_groups()

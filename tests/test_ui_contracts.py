"""Static and rendered contracts for Telegram UI and persistent FSM payloads."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from string import Formatter
from types import SimpleNamespace

from bot.handlers.admin.economy import eco_groups
from bot.keyboards import achievements as k_achievements
from bot.keyboards import admin as k_admin
from bot.keyboards import admin_panel as k_admin_panel
from bot.keyboards import admin_promos as k_admin_promos
from bot.keyboards import admin_reviews as k_admin_reviews
from bot.keyboards import bonus as k_bonus
from bot.keyboards import clicker as k_clicker
from bot.keyboards import history as k_history
from bot.keyboards import gifts as k_gifts
from bot.keyboards import instructions as k_instructions
from bot.keyboards import leaderboard as k_leaderboard
from bot.keyboards import main_menu as k_main_menu
from bot.keyboards import notifications as k_notifications
from bot.keyboards import onboarding as k_onboarding
from bot.keyboards import partner as k_partner
from bot.keyboards import promo as k_promo
from bot.keyboards import referral as k_referral
from bot.keyboards import reviews as k_reviews
from bot.keyboards import sections as k_sections
from bot.keyboards import support as k_support
from bot.keyboards import tasks as k_tasks
from bot.keyboards import wheel as k_wheel
from db.models import SponsorKind, TicketStatus
from locales.ru import T
from userbot.gifts import Gift


ROOT = Path(__file__).resolve().parents[1]
MAX_DB_ID = 9_223_372_036_854_775_807


def _sample_markups() -> list:
    sponsor = SimpleNamespace(
        id=MAX_DB_ID,
        title="S" * 255,
        kind=SponsorKind.PUBLIC.value,
        username="sirius_channel",
        invite_link=None,
        is_required=False,
        is_active=True,
        reward=12.5,
        subs_limit=100,
        subs_counter=7,
    )
    required_sponsor = SimpleNamespace(**{**vars(sponsor), "is_required": True})
    task = SimpleNamespace(sponsor=sponsor, is_completed=False)
    link = SimpleNamespace(id=MAX_DB_ID, title="L" * 255)
    promo = SimpleNamespace(
        id=MAX_DB_ID,
        code="X" * 64,
        is_active=True,
        is_honeypot=False,
        used_count=5,
        max_activations=10,
    )
    instruction = SimpleNamespace(id=MAX_DB_ID, title="I" * 255)
    user = SimpleNamespace(id=MAX_DB_ID, is_banned=False, is_shadow_banned=False)
    open_ticket = SimpleNamespace(
        id=MAX_DB_ID,
        user_id=MAX_DB_ID,
        subject="T" * 255,
        status=TicketStatus.NEW.value,
    )
    closed_ticket = SimpleNamespace(
        **{**vars(open_ticket), "status": TicketStatus.CLOSED.value}
    )
    groups = eco_groups()
    gift = Gift(gift_id=MAX_DB_ID, title="G" * 128, stars=15)
    gift_request = SimpleNamespace(id=MAX_DB_ID, title="G" * 128, status="pending", reserve_state="held")
    gift_unknown = SimpleNamespace(**{**vars(gift_request), "status": "reconciliation_required"})
    gift_waiting = SimpleNamespace(**{**vars(gift_request), "status": "waiting_funds"})

    markups = [
        k_achievements.kb_achievements(),
        k_bonus.kb_bonus(can_claim=True),
        k_bonus.kb_bonus(can_claim=False),
        k_clicker.kb_clicker(can_click=True),
        k_clicker.kb_clicker(can_click=True, cooldown_ms_left=60_000),
        k_clicker.kb_clicker(can_click=False),
        k_clicker.kb_clicker_captcha("x" * 16, ("🍎", "🍋", "🍇", "🍉")),
        k_history.kb_history(1, 1),
        k_history.kb_history(2, 3),
        k_instructions.kb_instruction_page(0, 1),
        k_instructions.kb_instruction_page(1, 3),
        k_leaderboard.kb_leaderboard("week"),
        k_leaderboard.kb_leaderboard("month"),
        k_leaderboard.kb_leaderboard("all"),
        k_main_menu.kb_main_menu(),
        k_main_menu.kb_main_menu(channel_url="https://t.me/sirius"),
        k_gifts.kb_catalogue([gift], page=1, pages=3),
        k_gifts.kb_gift(MAX_DB_ID, available=True),
        k_gifts.kb_gift(MAX_DB_ID, available=False),
        k_gifts.kb_confirmation("x" * 32, cost="15 ед."),
        k_gifts.kb_gift_history([gift_request]),
        k_gifts.kb_request(gift_request),
        k_gifts.kb_cancel_confirmation(MAX_DB_ID),
        k_gifts.kb_gift_error(),
        k_gifts.kb_admin_gifts(),
        k_gifts.kb_admin_list([gift_request], section="reconciliation_required"),
        k_gifts.kb_admin_request(gift_unknown),
        k_gifts.kb_admin_request(gift_waiting),
        k_gifts.kb_admin_cancel(MAX_DB_ID),
        k_gifts.kb_admin_decision(MAX_DB_ID, "x" * 32),
        k_notifications.kb_notifications({"refs": True, "tasks": False}),
        k_onboarding.kb_terms_page(1, 3),
        k_onboarding.kb_terms_page(3, 3),
        k_onboarding.kb_captcha(("🍎", "🍋", "🍇", "🍉"), "x" * 16),
        k_onboarding.kb_subs([sponsor]),
        k_partner.kb_partner_root(),
        k_partner.kb_partner_links([link]),
        k_partner.kb_partner_link_card(MAX_DB_ID),
        k_partner.kb_partner_sponsors(),
        k_partner.kb_partner_payout_method(),
        k_partner.kb_partner_cancel(),
        k_partner.kb_partner_back(),
        k_promo.kb_promo_intro(),
        k_promo.kb_promo_waiting(),
        k_promo.kb_promo_result(),
        k_referral.kb_referral(share_url="https://t.me/share/url?url=test"),
        k_referral.kb_referral_text_view(),
        k_reviews.kb_review_intro(),
        k_reviews.kb_review_rating(5),
        k_reviews.kb_review_text_step(),
        k_reviews.kb_review_anonymity(),
        k_reviews.kb_review_confirm(),
        k_reviews.kb_review_success(),
        k_sections.kb_earn(),
        k_sections.kb_help(),
        k_sections.kb_profile(is_partner=False),
        k_sections.kb_profile(is_partner=True),
        k_support.kb_support_home(),
        k_support.kb_faq_list(["Q" * 500]),
        k_support.kb_faq_answer(),
        k_support.kb_support_cancel(),
        k_support.kb_support_reply_cancel(MAX_DB_ID),
        k_support.kb_support_close_confirm(MAX_DB_ID),
        k_support.kb_support_created(),
        k_support.kb_my_tickets([open_ticket]),
        k_support.kb_ticket_card(open_ticket),
        k_support.kb_ticket_card(closed_ticket),
        k_support.kb_open_ticket_dm(MAX_DB_ID),
        k_support.kb_admin_sup_list(
            [open_ticket], {MAX_DB_ID: "U" * 255}
        ),
        k_support.kb_admin_sup_list(
            [closed_ticket], {MAX_DB_ID: "U" * 255}, archive=True
        ),
        k_support.kb_admin_sup_card(open_ticket),
        k_support.kb_admin_sup_card(closed_ticket, from_archive=True),
        k_support.kb_admin_sup_reply_cancel(MAX_DB_ID),
        k_support.kb_admin_sup_close_confirm(MAX_DB_ID),
        k_tasks.kb_tasks_list([task]),
        k_tasks.kb_task_card(
            MAX_DB_ID, "https://t.me/sirius", is_completed=False
        ),
        k_tasks.kb_task_card(MAX_DB_ID, None, is_completed=True),
        k_wheel.kb_wheel(free_available=True, can_pay=True, cost=5),
        k_wheel.kb_wheel(free_available=False, can_pay=False, cost=5),
        k_wheel.kb_paid_confirmation(token="x" * 16, cost=5),
        k_admin.kb_admin_root(),
        k_admin.kb_sponsors_list([sponsor]),
        k_admin.kb_sponsor_card(sponsor),
        k_admin.kb_sponsor_card(required_sponsor),
        k_admin.kb_sponsor_delete_confirm(MAX_DB_ID),
        k_admin.kb_add_kind(),
        k_admin.kb_add_cancel(),
        k_admin_panel.kb_dash("adm:dash"),
        k_admin_panel.kb_user_search(),
        k_admin_panel.kb_user_card(user),
        k_admin_panel.kb_eco_groups(sorted(groups)),
        k_admin_panel.kb_bc_cancel(),
        k_admin_panel.kb_bc_confirm(),
        k_admin_panel.kb_ins_list([instruction]),
        k_admin_panel.kb_ins_card(MAX_DB_ID),
        k_admin_panel.kb_ins_cancel(),
        k_admin_panel.kb_channel(),
        k_admin_panel.kb_stop_words(),
        k_admin_panel.kb_sw_cancel(),
        k_admin_panel.kb_pa_root([(MAX_DB_ID, "P" * 255)], pending=1),
        k_admin_panel.kb_pa_card(MAX_DB_ID, is_active=True),
        k_admin_panel.kb_pa_payouts([(MAX_DB_ID, "P" * 255)]),
        k_admin_panel.kb_pa_payout_card(MAX_DB_ID),
        k_admin_panel.kb_pa_cancel(),
        k_admin_promos.kb_promos_list([promo]),
        k_admin_promos.kb_promo_card(promo),
        k_admin_promos.kb_promo_delete_confirm(MAX_DB_ID),
        k_admin_promos.kb_promo_add_cancel(),
        k_admin_promos.kb_promo_add_honeypot(),
        k_admin_reviews.kb_reviews_list(),
        k_admin_reviews.kb_review_mod_actions(MAX_DB_ID),
    ]
    for group, keys in groups.items():
        markups.append(k_admin_panel.kb_eco_keys(group, keys))
        markups.append(k_admin_panel.kb_eco_cancel(group))
    return markups


def _all_callbacks(markups: list) -> list[str]:
    return [
        button.callback_data
        for markup in markups
        for row in markup.inline_keyboard
        for button in row
        if button.callback_data is not None
    ]


def _mentions_f_data(node: ast.AST) -> bool:
    return any(
        isinstance(item, ast.Attribute)
        and item.attr == "data"
        and isinstance(item.value, ast.Name)
        and item.value.id == "F"
        for item in ast.walk(node)
    )


def _patterns(node: ast.AST) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for item in ast.walk(node):
        if isinstance(item, ast.Compare) and _mentions_f_data(item.left):
            for op, comparator in zip(item.ops, item.comparators, strict=True):
                if (
                    isinstance(op, ast.Eq)
                    and isinstance(comparator, ast.Constant)
                    and isinstance(comparator.value, str)
                ):
                    found.append(("exact", comparator.value))
        if not isinstance(item, ast.Call) or not isinstance(item.func, ast.Attribute):
            continue
        if (
            item.func.attr == "startswith"
            and _mentions_f_data(item.func.value)
            and item.args
            and isinstance(item.args[0], ast.Constant)
            and isinstance(item.args[0].value, str)
        ):
            found.append(("prefix", item.args[0].value))
        if (
            item.func.attr == "in_"
            and _mentions_f_data(item.func.value)
            and item.args
            and isinstance(item.args[0], (ast.Set, ast.Tuple, ast.List))
        ):
            found.extend(
                ("exact", value.value)
                for value in item.args[0].elts
                if isinstance(value, ast.Constant) and isinstance(value.value, str)
            )
    return found


def _handler_patterns() -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    all_patterns: list[tuple[str, str]] = []
    unscoped_patterns: list[tuple[str, str]] = []
    for path in (ROOT / "bot" / "handlers").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        functions = (
            item
            for item in ast.walk(tree)
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
        for function in functions:
            for decorator in function.decorator_list:
                if not (
                    isinstance(decorator, ast.Call)
                    and isinstance(decorator.func, ast.Attribute)
                    and decorator.func.attr == "callback_query"
                ):
                    continue
                patterns = _patterns(decorator)
                all_patterns.extend(patterns)
                state_scoped = any(
                    not _mentions_f_data(argument) for argument in decorator.args
                )
                if not state_scoped:
                    unscoped_patterns.extend(patterns)
    return all_patterns, unscoped_patterns


def _matches(callback_data: str, patterns: list[tuple[str, str]]) -> bool:
    return any(
        callback_data == value if kind == "exact" else callback_data.startswith(value)
        for kind, value in patterns
    )


def test_all_rendered_keyboards_respect_telegram_limits() -> None:
    for markup in _sample_markups():
        for row in markup.inline_keyboard:
            assert len(row) <= 8
            for button in row:
                if button.callback_data is not None:
                    assert len(button.callback_data.encode("utf-8")) <= 64


def test_all_rendered_callbacks_have_handlers() -> None:
    patterns, _ = _handler_patterns()
    uncovered = sorted(
        callback
        for callback in set(_all_callbacks(_sample_markups()))
        if not _matches(callback, patterns)
    )
    assert uncovered == []


def test_state_scoped_callbacks_have_stale_fallbacks() -> None:
    all_patterns, unscoped_patterns = _handler_patterns()
    # A pattern present only behind an FSM state would leave a stale inline button
    # spinning forever after a restart or after the dialogue has moved on.
    missing: list[str] = []
    for kind, value in all_patterns:
        sample = value if kind == "exact" else value + "sample"
        if not _matches(sample, unscoped_patterns):
            missing.append(sample)
    assert sorted(set(missing)) == []


def test_keyboards_expose_implemented_gifts_and_antifraud() -> None:
    markups = _sample_markups()
    callbacks = _all_callbacks(markups)
    texts = [
        button.text.lower()
        for markup in markups
        for row in markup.inline_keyboard
        for button in row
    ]
    # Legacy withdrawal handlers are replaced by the implemented gift flow.
    # The existing withdraw.* admission settings remain editable in economy.
    assert "gift:open" in callbacks
    assert not any(callback.startswith("withdraw") for callback in callbacks)
    assert not any(":shon:" in callback or ":shoff:" in callback for callback in callbacks)
    assert "adm:af:open" in callbacks
    assert not any("nft" in text or "сезон" in text or "миссии" in text for text in texts)


def test_locale_format_calls_match_template_placeholders() -> None:
    source_roots = ("bot", "services", "workers", "utils", "userbot", "core", "db")
    paths = [path for root in source_roots for path in (ROOT / root).rglob("*.py")]
    paths.append(ROOT / "main.py")
    problems: list[str] = []
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for call in ast.walk(tree):
            if not (
                isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
                and call.func.attr == "format"
                and isinstance(call.func.value, ast.Attribute)
                and isinstance(call.func.value.value, ast.Name)
                and call.func.value.value.id == "T"
            ):
                continue
            key = call.func.value.attr
            template = getattr(T, key, None)
            if not isinstance(template, str):
                problems.append(f"{path.relative_to(ROOT)}:{call.lineno}: T.{key} missing")
                continue
            fields = {
                field.split(".", 1)[0].split("[", 1)[0]
                for _, field, _, _ in Formatter().parse(template)
                if field
            }
            keywords = {item.arg for item in call.keywords if item.arg is not None}
            if call.args or any(item.arg is None for item in call.keywords):
                problems.append(
                    f"{path.relative_to(ROOT)}:{call.lineno}: T.{key} uses non-static format args"
                )
            elif fields != keywords:
                problems.append(
                    f"{path.relative_to(ROOT)}:{call.lineno}: T.{key} "
                    f"expects {sorted(fields)}, got {sorted(keywords)}"
                )
    assert problems == []


def test_fsm_update_payloads_are_reviewed_json_primitives() -> None:
    allowed_keys = {
        "bc_text",
        "captcha_answer",
        "captcha_attempts_left",
        "captcha_token",
        "chat_id",
        "code",
        "eco_key",
        "expires_at_iso",
        "ins_id",
        "ins_page",
        "ins_title",
        "ins_total",
        "invite_link",
        "is_anonymous",
        "kind",
        "max_activations",
        "mod_action",
        "mod_review_id",
        "pa_id",
        "payout_method",
        "rating",
        "reward",
        "sponsor_id",
        "suggested_title",
        "target_user_id",
        "text",
        "ticket_id",
        "total_steps",
        "ui_chat_id",
        "ui_message_id",
        "wheel_paid_token",
        "wheel_paid_cost",
        "wheel_paid_expires_at",
        "gift_quote_token",
        "gift_quote_expires_at",
        "gift_cancel_request_id",
        "gift_admin_request_id",
        "gift_admin_action",
        "gift_admin_evidence",
        "gift_admin_token",
        "antifraud_expiry",
        "antifraud_owner",
        "antifraud_user_id",
        "antifraud_reason",
        "antifraud_token",
        "username",
    }
    observed: set[str] = set()
    problems: list[str] = []
    for path in (ROOT / "bot" / "handlers").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for call in ast.walk(tree):
            if not (
                isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
                and call.func.attr == "update_data"
            ):
                continue
            if call.args or any(keyword.arg is None for keyword in call.keywords):
                problems.append(
                    f"{path.relative_to(ROOT)}:{call.lineno}: update_data must use explicit keywords"
                )
                continue
            observed.update(keyword.arg for keyword in call.keywords if keyword.arg)
    assert problems == []
    assert observed == allowed_keys

    # Representative runtime types for every reviewed key are accepted by the
    # SQLite storage's strict JSON codec; dates are deliberately persisted as ISO.
    representative = {
        key: (
            None
            if key in {"expires_at_iso", "invite_link", "username"}
            else False
            if key == "is_anonymous"
            else 1.5
            if key in {"reward", "wheel_paid_cost"}
            else 1
            if key.endswith("_id")
            or key
            in {
                "captcha_attempts_left",
                "chat_id",
                "ins_page",
                "ins_total",
                "max_activations",
                "rating",
                "total_steps",
                "wheel_paid_expires_at",
            }
            else "value"
        )
        for key in allowed_keys
    }
    json.dumps(representative, ensure_ascii=False)

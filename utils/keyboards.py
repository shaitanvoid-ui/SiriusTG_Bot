"""Native Telegram button hierarchy shared by every SIRIUS screen."""

from __future__ import annotations

from typing import Any

from aiogram.types import DisabledButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def action_style(callback: str | None) -> str | None:
    """Color actions, never navigation or a disabled/placeholder button."""
    if not callback:
        return None
    if callback in {"sec:earn", "day:open", "ref:open"}:
        return "primary"
    if callback in {"bns:claim", "clk:tap", "whl:spin:free", "terms:accept"}:
        return "success"
    if callback.startswith(("tsk:check:", "rev:approve:", "adm:rev:approve:")):
        return "success"
    # Only the final destructive confirmation is red; ordinary navigation stays neutral.
    if ":del_yes:" in callback or ":close_yes:" in callback or ":ban:" in callback:
        return "danger"
    return None


class SiriusKeyboardBuilder(InlineKeyboardBuilder):
    def as_markup(self, **kwargs: Any) -> InlineKeyboardMarkup:
        markup = super().as_markup(**kwargs)
        for row in markup.inline_keyboard:
            for button in row:
                text = " ".join(button.text.split())
                button.text = text if len(text) <= 48 else text[:47].rstrip() + "…"
                if button.style is None:
                    button.style = None if button.text.startswith("⏳") else action_style(button.callback_data)
                if button.callback_data in {"bns:noop", "clk:noop", "whl:noop", "ins:noop", "hist:noop"}:
                    button.disabled = DisabledButton()
                    button.callback_data = None
        return markup

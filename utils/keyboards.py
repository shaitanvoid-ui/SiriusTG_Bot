"""Native Telegram button hierarchy shared by every SIRIUS screen."""

from __future__ import annotations

from typing import Any

from aiogram.types import DisabledButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def action_style(callback: str | None) -> str | None:
    """Color actions, never navigation or a disabled/placeholder button."""
    if not callback:
        return None
    if callback in {"bns:claim", "clk:tap", "whl:spin:free"}:
        return "success"
    if callback.startswith(("tsk:claim:", "tsk:check:", "rev:approve:", "adm:rev:approve:")):
        return "success"
    if callback in {
        "terms:accept", "subs:check", "promo:start", "rev:start",
        "rev:rating_next", "rev:confirm", "sup:new", "whl:confirm", "adm:bc:go",
    } or callback.startswith(("gift:quote:", "gift:confirm:", "whl:paid:", "sup:t:reply:", "adm:sup:reply:")):
        return "primary"
    # Only the final destructive confirmation is red; ordinary navigation stays neutral.
    if ":del_yes:" in callback or ":close_yes:" in callback or callback.startswith(("gift:cancel_yes:", "adm:gift:decide:")):
        return "danger"
    return None


class SiriusKeyboardBuilder(InlineKeyboardBuilder):
    def footer(self, *, text: str, callback_data: str) -> None:
        """Keep the parent on the left and the screen's home on the right."""
        from locales.ru import T

        self.button(text=text, callback_data=callback_data)
        home = "adm:root" if callback_data.startswith("adm:") else "nav:menu"
        callbacks = [callback_data]
        if callback_data not in {"nav:menu", "adm:root"}:
            self.button(text=T.btn_back_admin if home == "adm:root" else T.btn_back_menu, callback_data=home)
            callbacks.append(home)
        self._footer_callbacks = callbacks

    def as_markup(self, **kwargs: Any) -> InlineKeyboardMarkup:
        markup = super().as_markup(**kwargs)
        footer_callbacks = getattr(self, "_footer_callbacks", ())
        if footer_callbacks:
            footer_buttons = {}
            content = []
            for row in markup.inline_keyboard:
                remaining = []
                for button in row:
                    if button.callback_data in footer_callbacks:
                        footer_buttons[button.callback_data] = button
                    else:
                        remaining.append(button)
                if remaining:
                    content.append(remaining)
            content.append([footer_buttons[callback] for callback in footer_callbacks])
            markup.inline_keyboard = content
        for row in markup.inline_keyboard:
            for button in row:
                text = " ".join(button.text.split())
                button.text = text if len(text) <= 48 else text[:47].rstrip() + "…"
                if button.callback_data in {"bns:noop", "clk:noop", "whl:noop", "ins:noop", "hist:noop"}:
                    button.disabled = DisabledButton()
                    button.callback_data = None
                if button.disabled is not None:
                    button.style = None
                elif button.style is None:
                    button.style = action_style(button.callback_data)
        return markup

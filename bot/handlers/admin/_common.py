"""Общие хелперы админ-хендлеров (вынесены из дублей, тех-долг 2026-06-10)."""

from __future__ import annotations

from db.models import User


def user_label(user: User | None) -> str:
    """Читаемое имя юзера для админ-списков: @username → имя → tg_id."""
    if user is None:
        return "?"
    if user.username:
        return f"@{user.username}"
    return user.first_name or str(user.tg_id)

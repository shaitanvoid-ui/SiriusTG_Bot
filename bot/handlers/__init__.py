from __future__ import annotations

from aiogram import Router

from bot.handlers import (
    achievements,
    bonus,
    captcha,
    clicker,
    history,
    instructions,
    leaderboard,
    menu,
    notifications,
    partner,
    profile,
    promo,
    referral,
    reviews,
    sections,
    start,
    sub_gate,
    support,
    tasks,
    terms,
    wheel,
)
from bot.handlers.admin import broadcast as admin_broadcast
from bot.handlers.admin import channel as admin_channel
from bot.handlers.admin import dashboard as admin_dashboard
from bot.handlers.admin import economy as admin_economy
from bot.handlers.admin import instructions as admin_instructions
from bot.handlers.admin import partners as admin_partners
from bot.handlers.admin import promos as admin_promos
from bot.handlers.admin import reviews as admin_reviews
from bot.handlers.admin import sponsors as admin_sponsors
from bot.handlers.admin import stop_words as admin_stop_words
from bot.handlers.admin import support as admin_support
from bot.handlers.admin import users as admin_users


def get_root_router() -> Router:
    root = Router(name="root")
    # админка регистрируется первой — её фильтры IsAdmin
    root.include_router(admin_sponsors.router)
    root.include_router(admin_promos.router)
    root.include_router(admin_reviews.router)
    root.include_router(admin_dashboard.router)
    root.include_router(admin_users.router)
    root.include_router(admin_economy.router)
    root.include_router(admin_broadcast.router)
    root.include_router(admin_instructions.router)
    root.include_router(admin_channel.router)
    root.include_router(admin_stop_words.router)
    root.include_router(admin_partners.router)
    root.include_router(admin_support.router)
    # онбординг
    root.include_router(start.router)
    root.include_router(terms.router)
    root.include_router(captcha.router)
    root.include_router(sub_gate.router)
    # основное
    root.include_router(menu.router)
    root.include_router(profile.router)
    root.include_router(referral.router)
    root.include_router(sections.router)
    root.include_router(clicker.router)
    root.include_router(tasks.router)
    root.include_router(promo.router)
    root.include_router(bonus.router)
    root.include_router(wheel.router)
    root.include_router(achievements.router)
    root.include_router(leaderboard.router)
    root.include_router(instructions.router)
    root.include_router(reviews.router)
    root.include_router(partner.router)
    root.include_router(support.router)
    root.include_router(notifications.router)
    root.include_router(history.router)
    return root


__all__ = ["get_root_router"]

from __future__ import annotations

from aiogram import Router

from bot.handlers import (
    achievements,
    bonus,
    captcha,
    clicker,
    daily,
    errors,
    gifts,
    history,
    instructions,
    leaderboard,
    menu,
    notifications,
    navigation,
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
from bot.handlers.admin import gifts as admin_gifts
from bot.handlers.admin import instructions as admin_instructions
from bot.handlers.admin import partners as admin_partners
from bot.handlers.admin import promos as admin_promos
from bot.handlers.admin import reviews as admin_reviews
from bot.handlers.admin import sponsors as admin_sponsors
from bot.handlers.admin import stop_words as admin_stop_words
from bot.handlers.admin import support as admin_support
from bot.handlers.admin import users as admin_users
from bot.handlers.admin import antifraud as admin_antifraud
from bot.middlewares.gates import (
    CaptchaGateMiddleware,
    SubGateMiddleware,
    TermsGateMiddleware,
)
from bot.middlewares.navigation import NavigationStateMiddleware


def _build_ready_router() -> Router:
    """Пользовательские разделы, доступные только после всех onboarding-гейтов."""
    ready = Router(name="ready")
    for observer in (ready.message, ready.callback_query):
        observer.middleware(TermsGateMiddleware())
        observer.middleware(CaptchaGateMiddleware())
        observer.middleware(SubGateMiddleware())
    ready.callback_query.middleware(NavigationStateMiddleware())

    ready.include_router(menu.router)
    ready.include_router(daily.router)
    ready.include_router(profile.router)
    ready.include_router(gifts.router)
    ready.include_router(referral.router)
    ready.include_router(sections.router)
    ready.include_router(clicker.router)
    ready.include_router(tasks.router)
    ready.include_router(promo.router)
    ready.include_router(bonus.router)
    ready.include_router(wheel.router)
    ready.include_router(achievements.router)
    ready.include_router(leaderboard.router)
    ready.include_router(instructions.router)
    ready.include_router(reviews.router)
    ready.include_router(partner.router)
    ready.include_router(support.router)
    ready.include_router(notifications.router)
    ready.include_router(history.router)
    ready.include_router(navigation.router)
    return ready


def get_root_router() -> Router:
    root = Router(name="root")
    root.errors.register(errors.on_unhandled_error)
    # админка регистрируется первой — её фильтры IsAdmin
    root.include_router(admin_sponsors.router)
    root.include_router(admin_promos.router)
    root.include_router(admin_reviews.router)
    root.include_router(admin_dashboard.router)
    root.include_router(admin_users.router)
    root.include_router(admin_antifraud.router)
    root.include_router(admin_economy.router)
    root.include_router(admin_gifts.router)
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
    # основное: middleware стоят только на ready, onboarding/admin не блокируются
    root.include_router(_build_ready_router())
    return root


__all__ = ["get_root_router"]

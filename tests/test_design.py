"""Дизайн-полировка: приветствие, лесенка стрика, анимация колеса,
прогресс-бары достижений, вехи кликера, продуктовая политика текстов."""

from __future__ import annotations

from bot.handlers.bonus import _ladder
from bot.handlers.menu import greeting_for_hour
from locales.ru import T
from utils.ui import mini_bar


# ---------- приветствие по времени суток ----------

def test_greeting_morning():
    assert greeting_for_hour(7) == T.greeting_morning


def test_greeting_day():
    assert greeting_for_hour(13) == T.greeting_day


def test_greeting_evening():
    assert greeting_for_hour(20) == T.greeting_evening


def test_greeting_night():
    assert greeting_for_hour(2) == T.greeting_night
    assert greeting_for_hour(23) == T.greeting_night


def test_menu_caption_has_greeting_placeholder():
    assert "{greeting}" in T.menu_caption


# ---------- лесенка стрика ----------

_TIERS = {1: 0.5, 3: 0.7, 7: 1.0, 14: 1.5, 30: 2.0}


def test_ladder_marks_done_next_locked():
    out = _ladder(_TIERS, streak=3)
    lines = out.split("\n")
    assert len(lines) == 5
    assert lines[0].startswith("✓") and "День 1" in lines[0]
    assert lines[1].startswith("✓") and "День 3" in lines[1]
    assert "следующая ступень" in lines[2] and "День 7" in lines[2]
    assert not lines[3].startswith("✓") and "День 14" in lines[3]
    assert not lines[4].startswith("✓") and "День 30" in lines[4]


def test_ladder_all_done_at_max():
    out = _ladder(_TIERS, streak=30)
    assert "следующая ступень" not in out
    assert out.count("✓") == 5


def test_bonus_caption_has_ladder_placeholder():
    assert "{ladder}" in T.bonus_caption


# ---------- колесо: кадры анимации ----------

def test_wheel_spin_frames_present():
    assert len(T.wheel_spin_frames) >= 2
    for frame in T.wheel_spin_frames:
        assert "колесо" in frame.lower()
        # кадры — чистый текст без format-плейсхолдеров
        assert "{" not in frame


# ---------- достижения: мини-бар ----------

def test_mini_bar_bounds():
    assert mini_bar(0, 10) == "▱" * 8
    assert mini_bar(10, 10) == "▰" * 8
    assert mini_bar(5, 10).count("▰") == 4


def test_ach_locked_row_has_bar():
    rendered = T.ach_row_locked.format(
        emoji="👆", name="Кликер", bar=mini_bar(100, 500),
        current=100, threshold=500, unit="тапов", reward="2.00⭐",
    )
    assert "▰" in rendered or "▱" in rendered
    assert "100/500" in rendered


# ---------- кликер: вехи ----------

def test_clicker_milestone_locales():
    assert "{clicks}" in T.clicker_milestone_alert
    assert "{earned}" in T.clicker_finish_alert


# ---------- продуктовая политика текстов ----------

def test_review_intro_no_low_rating_mention():
    rendered = T.review_intro.format(
        min_refs=3, cooldown_days=7, min_len=30, max_len=500, reward=1.0
    )
    assert "Низкие оценки" not in rendered


def test_no_multiplier_noise_in_cards():
    # множитель кликера фиксирован — «×1.00» больше не показываем
    assert "click_mult" not in T.menu_caption
    assert "click_mult" not in T.profile_caption
    assert "click_mult" not in T.clicker_caption


# ---------- алерты: callback.answer не рендерит HTML ----------

def test_alert_locales_have_no_html():
    """Telegram показывает callback-алерты плоским текстом — теги вылезают как <b></b>."""
    import re

    tag = re.compile(r"</?[a-z]+>")
    alert_keys = [
        k for k, v in vars(T).items() if isinstance(v, str) and k.endswith("_alert")
    ]
    # строки, которые тоже уходят в callback.answer, но без суффикса _alert
    extra = [
        "captcha_ok", "captcha_wrong", "captcha_failed",
        "subs_all_ok", "subs_not_subscribed",
        "forbidden", "banned",
        "review_already_done", "review_not_found",
        "admin_user_not_found", "admin_sponsor_deleted", "admin_promo_deleted",
        "admin_ins_deleted", "admin_pa_user_not_found", "error_generic",
    ]
    assert alert_keys, "ни одного *_alert ключа не нашлось — проверь нейминг"
    for key in alert_keys + extra:
        value = getattr(T, key)
        assert not tag.search(value), f"{key} содержит HTML-теги — в алерте они видны как текст"

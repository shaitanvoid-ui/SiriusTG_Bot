"""Задача 1: 6-я страница соглашения без блока «Личные данные»."""

from __future__ import annotations

from locales.ru import T


def test_terms_pages_count_unchanged():
    assert len(T.terms_pages_bodies) == 6


def test_personal_data_block_removed():
    page6 = T.terms_pages_bodies[5]
    assert "Личные данные" not in page6
    assert "Ответственность" in page6
    assert "Изменения" in page6
    # финальная строка соглашения на месте
    assert "Принимаю" in page6


def test_notify_task_lost_locale_present():
    assert hasattr(T, "notify_task_lost")
    rendered = T.notify_task_lost.format(title="Канал", amount="2.00⭐")
    assert "Канал" in rendered
    assert "2.00⭐" in rendered


def test_log_task_lost_locale_present():
    assert hasattr(T, "log_task_lost")
    assert hasattr(T, "log_tasks_recheck_summary")

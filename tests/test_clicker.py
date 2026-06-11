"""Кликер: Бронза 40×0.1⭐=4⭐, Алмаз 100×0.1⭐=10⭐, rate-limit 5 мин, мини-капча."""

from __future__ import annotations

from db.repositories.clicker_day import ClickerDayRepo
from db.repositories.user import UserRepo
from services.clicker import CaptchaStatus, ClickerService, ClickStatus, _today
from services.settings import SettingsService
from tests.helpers import create_user


async def test_bronze_daily_limit_is_40_and_total_is_4(session):
    user = await create_user(session, tg_id=999000001)  # 0 рефов → Бронза
    svc = ClickerService(session, SettingsService(session))
    repo = ClickerDayRepo(session)
    today = _today()

    ok_clicks = 0
    captcha_count = 0
    guard = 0
    while True:
        guard += 1
        assert guard < 500, "слишком много итераций — возможен зацикл"
        # сбрасываем rate-limit перед каждым кликом
        day = await repo.get_or_create(user.id, today)
        day.last_click_ms = 0
        await session.flush()

        res = await svc.click(user)
        if res.status == ClickStatus.NEED_CAPTCHA:
            captcha_count += 1
            answer = (set(res.captcha_choices) - set(res.captcha_hint)).pop()
            sub = await svc.submit_captcha(user, token=res.captcha_token, choice=answer)
            assert sub.status == CaptchaStatus.OK
            continue
        if res.status == ClickStatus.DAILY_LIMIT:
            break
        assert res.status == ClickStatus.OK
        ok_clicks += 1

    assert ok_clicks == 40
    day = await repo.get_or_create(user.id, today)
    assert round(day.earned, 2) == 4.0
    assert captcha_count >= 1, "за 40 кликов мини-капча должна сработать"

    fresh = await UserRepo(session).get_by_id(user.id)
    assert round(fresh.balance, 2) == 4.0


async def test_diamond_cap_is_10(session):
    # 150 подтв. рефов → Алмаз → лимит 100 кликов × 0.1⭐ = 10⭐
    user = await create_user(session, tg_id=999000004, confirmed_ref_count=150)
    svc = ClickerService(session, SettingsService(session))
    repo = ClickerDayRepo(session)
    today = _today()

    view = await svc.get_view(user)
    assert view.daily_limit == 100
    assert view.level.name == "Алмаз"

    ok_clicks = 0
    guard = 0
    while True:
        guard += 1
        assert guard < 600, "слишком много итераций — возможен зацикл"
        day = await repo.get_or_create(user.id, today)
        day.last_click_ms = 0
        await session.flush()

        res = await svc.click(user)
        if res.status == ClickStatus.NEED_CAPTCHA:
            answer = (set(res.captcha_choices) - set(res.captcha_hint)).pop()
            sub = await svc.submit_captcha(user, token=res.captcha_token, choice=answer)
            assert sub.status == CaptchaStatus.OK
            continue
        if res.status == ClickStatus.DAILY_LIMIT:
            break
        assert res.status == ClickStatus.OK
        ok_clicks += 1

    assert ok_clicks == 100
    day = await repo.get_or_create(user.id, today)
    assert round(day.earned, 2) == 10.0

    fresh = await UserRepo(session).get_by_id(user.id)
    assert round(fresh.balance, 2) == 10.0


async def test_rate_limit_blocks_second_click(session):
    user = await create_user(session, tg_id=999000002)
    svc = ClickerService(session, SettingsService(session))

    r1 = await svc.click(user)
    assert r1.status == ClickStatus.OK
    r2 = await svc.click(user)
    assert r2.status == ClickStatus.TOO_FAST
    assert r2.retry_after_ms > 0

    # карточка должна знать остаток перезарядки (для таймера в UI)
    view = await svc.get_view(user)
    assert 0 < view.cooldown_ms_left <= 300000


def test_duration_formatting():
    from utils.ui import clock_mmss, human_duration

    assert human_duration(300000) == "5 мин"
    assert human_duration(272000) == "4 мин 32 сек"
    assert human_duration(45000) == "45 сек"
    assert human_duration(0) == "0 сек"
    assert clock_mmss(272000) == "4:32"
    assert clock_mmss(300000) == "5:00"
    assert clock_mmss(5000) == "0:05"


async def test_wrong_captcha_regenerates_then_ok(session):
    user = await create_user(session, tg_id=999000003)
    svc = ClickerService(session, SettingsService(session))
    repo = ClickerDayRepo(session)
    today = _today()

    # кликаем до появления капчи
    guard = 0
    res = None
    while True:
        guard += 1
        assert guard < 200
        day = await repo.get_or_create(user.id, today)
        day.last_click_ms = 0
        await session.flush()
        res = await svc.click(user)
        if res.status == ClickStatus.NEED_CAPTCHA:
            break
        assert res.status == ClickStatus.OK

    hint = set(res.captcha_hint)
    wrong = next(iter(hint))  # любой из подсказки — заведомо неверный ответ
    bad = await svc.submit_captcha(user, token=res.captcha_token, choice=wrong)
    assert bad.status == CaptchaStatus.WRONG
    assert bad.captcha_token is not None

    answer = (set(bad.captcha_choices) - set(bad.captcha_hint)).pop()
    good = await svc.submit_captcha(user, token=bad.captcha_token, choice=answer)
    assert good.status == CaptchaStatus.OK

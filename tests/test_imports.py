"""Сборка роутера и импорт воркеров — без БД."""

from __future__ import annotations


def test_root_router_builds():
    from bot.handlers import get_root_router

    router = get_root_router()
    assert len(router.sub_routers) > 0


def test_tasks_rechecker_importable():
    import workers.tasks_rechecker as w

    assert callable(w.run_tasks_rechecker)
    assert callable(w.register_jobs)


def test_sub_rechecker_importable():
    import workers.sub_rechecker as w

    assert callable(w.run_subrechecker)
    assert callable(w.register_jobs)


def test_main_module_importable():
    import main

    assert callable(main.run)


def test_userbot_modules_importable():
    from userbot import bio_reader, client

    assert callable(client.get_client)
    assert callable(client.disconnect)
    assert client.is_configured() in (True, False)
    assert callable(bio_reader.check_ref_in_bio)


def test_bonus_handler_importable():
    from bot.handlers import bonus

    assert bonus.router is not None


def test_leaderboard_payout_importable():
    import workers.leaderboard_payout as w

    assert callable(w.run_leaderboard_payout)
    assert callable(w.register_jobs)


def test_gamification_handlers_importable():
    from bot.handlers import achievements, leaderboard, wheel

    assert achievements.router is not None
    assert leaderboard.router is not None
    assert wheel.router is not None

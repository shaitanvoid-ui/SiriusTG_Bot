from __future__ import annotations

import os
from pathlib import Path
import sqlite3
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _alembic_env(db_file: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "ENV": "test",
            "BOT_TOKEN": "1234567890:LOCAL_TEST_TOKEN_DO_NOT_USE",
            "OWNER_ID": "1",
            "ADMIN_IDS": "",
            "LOG_CHANNEL_ID": "",
            "FERNET_KEY": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "DATABASE_URL": f"sqlite+aiosqlite:///{db_file.resolve().as_posix()}",
        }
    )
    return env


def _upgrade(db_file: Path, revision: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", revision],
        cwd=PROJECT_ROOT,
        env=_alembic_env(db_file),
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def test_atomic_migrations_backfill_and_sanitize_nullable_orphans(tmp_path: Path) -> None:
    db_file = tmp_path / "historical.db"
    initial = _upgrade(db_file, "0009")
    assert initial.returncode == 0, initial.stdout + initial.stderr

    timestamp = "2026-01-01 00:00:00"
    with sqlite3.connect(db_file) as connection:
        connection.executemany(
            """
            INSERT INTO users (
                id, tg_id, subs_passed_at, created_at, updated_at,
                partner_id, partner_link_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (1, 1001, None, timestamp, timestamp, None, None),
                (2, 1002, timestamp, timestamp, timestamp, None, None),
                (3, 1003, timestamp, timestamp, timestamp, 999, 999),
                (4, 1004, timestamp, timestamp, timestamp, None, None),
            ],
        )
        connection.execute("INSERT INTO partners (id, user_id) VALUES (1, 1)")
        connection.execute("UPDATE users SET partner_id = 1 WHERE id = 2")
        connection.execute(
            """
            INSERT INTO sponsors (
                id, title, partner_id, created_at, updated_at
            ) VALUES (1, 'legacy', 999, ?, ?)
            """,
            (timestamp, timestamp),
        )
        connection.execute(
            """
            INSERT INTO support_tickets (id, user_id, subject, text, review_id)
            VALUES (1, 2, 'legacy', 'must survive', 999)
            """
        )
        connection.commit()

    upgraded = _upgrade(db_file, "head")
    assert upgraded.returncode == 0, upgraded.stdout + upgraded.stderr

    with sqlite3.connect(db_file) as connection:
        rewarded = connection.execute(
            "SELECT partner_rewarded, partner_id FROM users WHERE id = 2"
        ).fetchone()
        unattributed = connection.execute(
            "SELECT partner_rewarded FROM users WHERE id = 4"
        ).fetchone()
        orphan_user_links = connection.execute(
            "SELECT partner_id, partner_link_id FROM users WHERE id = 3"
        ).fetchone()
        orphan_sponsor_link = connection.execute(
            "SELECT partner_id FROM sponsors WHERE id = 1"
        ).fetchone()
        preserved_ticket = connection.execute(
            "SELECT user_id, review_id, text FROM support_tickets WHERE id = 1"
        ).fetchone()
        preserved_partner = connection.execute(
            "SELECT user_id FROM partners WHERE id = 1"
        ).fetchone()
        connection.execute("PRAGMA foreign_keys=ON")
        fk_errors = connection.execute("PRAGMA foreign_key_check").fetchall()

    assert rewarded == (1, 1)
    assert unattributed == (0,)
    assert orphan_user_links == (None, None)
    assert orphan_sponsor_link == (None,)
    assert preserved_ticket == (2, None, "must survive")
    assert preserved_partner == (1,)
    assert fk_errors == []


def test_integrity_migration_fails_before_deleting_orphan_tickets(tmp_path: Path) -> None:
    db_file = tmp_path / "orphan-ticket.db"
    initial = _upgrade(db_file, "0009")
    assert initial.returncode == 0, initial.stdout + initial.stderr

    with sqlite3.connect(db_file) as connection:
        connection.execute(
            """
            INSERT INTO support_tickets (id, user_id, subject, text)
            VALUES (1, 999, 'orphan', 'preserve me')
            """
        )
        connection.commit()

    upgraded = _upgrade(db_file, "head")
    output = upgraded.stdout + upgraded.stderr
    assert upgraded.returncode != 0
    assert "found 1 orphan ticket(s); restore or quarantine them first" in output

    with sqlite3.connect(db_file) as connection:
        ticket = connection.execute(
            "SELECT user_id, text FROM support_tickets WHERE id = 1"
        ).fetchone()
    assert ticket == (999, "preserve me")

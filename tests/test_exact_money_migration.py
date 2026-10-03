"""Migration evidence on disposable databases, never the production file."""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from tests.test_atomic_migrations import PROJECT_ROOT, _alembic_env


def migrate(path: Path, command: str, revision: str):
    result = subprocess.run(
        [sys.executable, "-m", "alembic", command, revision],
        cwd=PROJECT_ROOT, env=_alembic_env(path), capture_output=True, text=True, timeout=60, check=False,
    )
    return result.returncode, result.stdout + result.stderr


def test_exact_money_empty_upgrade_downgrade_upgrade(tmp_path):
    path = tmp_path / "empty.db"
    assert migrate(path, "upgrade", "0014")[0] == 0
    assert migrate(path, "downgrade", "0013")[0] == 0
    code, output = migrate(path, "upgrade", "0014")
    assert code == 0, output
    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_legacy_money_has_explicit_rounding_audit_and_exact_safe_rollback(tmp_path):
    path = tmp_path / "historical.db"
    code, output = migrate(path, "upgrade", "0013")
    assert code == 0, output
    original_balance, original_debt = 11.00006, 0.30000000000000004
    timestamp = "2026-01-01 00:00:00"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT INTO users(id,tg_id,balance,debt,created_at,updated_at,bonus_streak,last_bonus_date) VALUES(1,9991,?,?,?,?,7,'2026-01-01')",
            (original_balance, original_debt, timestamp, timestamp),
        )
        connection.execute("INSERT INTO partners(id,user_id,balance,total_earned) VALUES(1,1,5.3,12.3)")
        connection.execute(
            "INSERT INTO partner_payouts(id,partner_id,amount_stars,rate_rub,amount_rub,method,requisites,status) VALUES(1,1,7,1.5,10.5,'card','fixture','pending')"
        )
        connection.commit()
    code, output = migrate(path, "upgrade", "0014")
    assert code == 0, output
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT balance_units,debt_units,bonus_streak,last_bonus_date FROM users").fetchone() == (110001, 3000, 7, "2026-01-01")
        assert connection.execute("SELECT balance_units,reserved_units,total_earned_units FROM partners").fetchone() == (53000, 70000, 123000)
        assert connection.execute("SELECT count(*) FROM money_operations WHERE reason='migration_opening'").fetchone() == (2,)
        for original, rounded, delta in connection.execute("SELECT original_value,rounded_units,rounding_delta FROM money_migration_audit"):
            assert Decimal(original) + Decimal(delta) == Decimal(rounded) / 10000
            assert abs(Decimal(delta)) <= Decimal("0.00005")
        user_journal = connection.execute("SELECT balance_after_units,debt_after_units FROM money_operations WHERE account_kind='user'").fetchone()
        assert user_journal == (110001, 3000)
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    code, output = migrate(path, "downgrade", "0013")
    assert code == 0, output
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT balance,debt FROM users").fetchone() == (original_balance, original_debt)
        assert connection.execute("SELECT amount_stars,status FROM partner_payouts").fetchone() == (7, "pending")
    code, output = migrate(path, "upgrade", "0014")
    assert code == 0, output


@pytest.mark.parametrize("activity", ["journal", "reserve", "unlogged_balance"])
def test_money_downgrade_fails_before_destructive_schema_changes(tmp_path, activity):
    path = tmp_path / "protected.db"
    assert migrate(path, "upgrade", "0013")[0] == 0
    with sqlite3.connect(path) as connection:
        connection.execute("INSERT INTO users(id,tg_id,balance,created_at,updated_at) VALUES(1,9991,10,'2026-01-01','2026-01-01')")
        connection.commit()
    assert migrate(path, "upgrade", "0014")[0] == 0
    with sqlite3.connect(path) as connection:
        if activity == "journal":
            connection.execute("INSERT INTO money_operations(account_kind,user_id,reason,balance_after_units) VALUES('user',1,'gift_reserve',100000)")
        elif activity == "reserve":
            connection.execute("UPDATE users SET reserved_units=10000")
        else:
            connection.execute("UPDATE users SET balance_units=90000")
        connection.commit()
    code, output = migrate(path, "downgrade", "0013")
    assert code != 0 and "downgrade refused" in output
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == ("0014",)
        assert "balance_units" in {row[1] for row in connection.execute("PRAGMA table_info(users)")}


def test_invalid_legacy_amount_fails_before_creating_any_columns(tmp_path):
    path = tmp_path / "invalid.db"
    assert migrate(path, "upgrade", "0013")[0] == 0
    with sqlite3.connect(path) as connection:
        connection.execute("INSERT INTO users(id,tg_id,balance,created_at,updated_at) VALUES(1,9991,-1,'2026-01-01','2026-01-01')")
        connection.commit()
    code, output = migrate(path, "upgrade", "0014")
    assert code != 0 and "invalid historical money" in output
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == ("0013",)
        assert "balance_units" not in {row[1] for row in connection.execute("PRAGMA table_info(users)")}
        assert connection.execute("SELECT balance FROM users").fetchone() == (-1.0,)

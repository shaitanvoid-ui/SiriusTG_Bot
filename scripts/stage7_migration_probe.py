"""Verify a disposable *copy* DB, including exact audit and reversible idle schema.

Never opens the source database. The caller decrypts a consistent Fernet backup
into isolated /tmp. No account or API data is printed.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from decimal import Decimal


def snapshot(path):
    with sqlite3.connect(path) as c:
        result = {}
        for (table,) in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
            if table in {"sqlite_sequence", "alembic_version"}:
                continue
            columns = sorted(row[1] for row in c.execute(f'PRAGMA table_info("{table}")'))
            projection = ",".join('"'+name+'"' for name in columns)
            result[table] = {"columns":columns, "rows":c.execute(f'SELECT {projection} FROM "{table}" ORDER BY rowid').fetchall()}
        return result


def migrate(path, operation, target):
    env = os.environ.copy()
    env.update(ENV="test", BOT_TOKEN="1234567890:LOCAL_TEST_TOKEN_DO_NOT_USE", OWNER_ID="1",
               FERNET_KEY="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
               DATABASE_URL=f"sqlite+aiosqlite:///{path.as_posix()}",
               TG_API_ID="", TG_API_HASH="", USERBOT_PHONE="")
    result = subprocess.run([sys.executable, "-m", "alembic", operation, target],
                            capture_output=True, text=True, env=env, timeout=60)
    if result.returncode:
        raise RuntimeError(result.stdout+result.stderr)


def run(path):
    if "copy" not in path.name or path.resolve().parent == Path("data").resolve():
        raise ValueError("Only an isolated disposable *copy* DB is allowed")
    before = snapshot(path)
    migrate(path, "upgrade", "head")
    with sqlite3.connect(path) as c:
        audit = c.execute("SELECT original_value,rounded_units,rounding_delta FROM money_migration_audit").fetchall()
        total_delta = Decimal(0)
        for original, units, delta in audit:
            assert Decimal(original)+Decimal(delta) == Decimal(units)/10000
            assert abs(Decimal(delta)) <= Decimal("0.00005")
            total_delta += Decimal(delta)
        assert c.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert c.execute("PRAGMA foreign_key_check").fetchall() == []
        assert c.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "0015"
        operations = c.execute("SELECT count(*) FROM money_operations").fetchone()[0]
        assert c.execute("SELECT count(*) FROM gift_requests").fetchone()[0] == 0
    migrate(path, "downgrade", "0013")
    after = snapshot(path)
    assert before == after, "idle rollback must restore every original value"
    migrate(path, "upgrade", "head")
    print(json.dumps({"revision":"0015", "audit_fields":len(audit),
                      "sum_rounding_delta":str(total_delta), "opening_operations":operations,
                      "integrity":"ok", "fk_violations":0,
                      "tables_preserved":len(before), "original_values_restored":True,
                      "idle_downgrade_reupgrade":True}))


if __name__ == "__main__":
    run(Path(sys.argv[1]).resolve())

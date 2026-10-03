"""Verify 0015 -> 0016 -> 0015 -> 0016 on an encrypted disposable copy only."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

from cryptography.fernet import Fernet


def snapshot(path: Path, tables=None):
    result = {}
    with sqlite3.connect(path) as connection:
        names = tables if tables is not None else [row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            if row[0] not in {"alembic_version", "sqlite_sequence"}]
        for name in names:
            safe = '"' + name.replace('"', '""') + '"'
            rows = connection.execute(f"SELECT * FROM {safe} ORDER BY rowid").fetchall()
            result[name] = {"rows": len(rows), "sha256": hashlib.sha256(
                json.dumps(rows, default=lambda value: value.hex(), ensure_ascii=False).encode()).hexdigest()}
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    return result


def migrate(path: Path, direction: str, revision: str) -> None:
    environment = dict(os.environ, ENV="test", OWNER_ID="1",
        BOT_TOKEN="1234567890:LOCAL_TEST_TOKEN_DO_NOT_USE",
        FERNET_KEY="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
        DATABASE_URL=f"sqlite+aiosqlite:///{path.as_posix()}",
        TG_API_ID="", TG_API_HASH="", USERBOT_PHONE="", USERBOT_ACCOUNT_ID="")
    result = subprocess.run([sys.executable, "-m", "alembic", direction, revision],
        env=environment, capture_output=True, timeout=90)
    if result.returncode:
        raise RuntimeError("Disposable-copy migration failed; live DB was not opened")
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone()[0] == revision


def main(encrypted: Path) -> None:
    if encrypted.suffix != ".fernet" or not encrypted.is_file():
        raise SystemExit("An existing encrypted backup is required")
    cipher = Fernet(os.environ["FERNET_KEY"].encode("ascii"))
    with tempfile.TemporaryDirectory(prefix="stage12_", dir="/tmp") as folder:
        copy = Path(folder) / "stage12-copy.db"
        copy.write_bytes(cipher.decrypt(encrypted.read_bytes()))
        with sqlite3.connect(copy) as connection:
            assert connection.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "0015"
        before = snapshot(copy)
        for direction, target in (("upgrade", "0016"), ("downgrade", "0015"), ("upgrade", "0016")):
            migrate(copy, direction, target)
            assert snapshot(copy, before) == before, "Original values changed in disposable copy"
        print(json.dumps({"revisions": "0015->0016->0015->0016", "tables_preserved": len(before),
            "rows_preserved": sum(item["rows"] for item in before.values()),
            "original_values_unchanged": True, "integrity": "ok", "fk_violations": 0}))


if __name__ == "__main__":
    try:
        main(Path(sys.argv[1]))
    except Exception as error:
        raise SystemExit(f"Copy probe failed: {type(error).__name__}") from None

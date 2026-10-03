"""Create and verify a consistent encrypted backup without printing DB contents.

Explicit maintenance command, run while the bot is stopped before migrations.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import sqlite3
from pathlib import Path

from cryptography.fernet import Fernet

from core.config import settings
from workers.db_backup import db_file_path, make_backup_file


async def main(folder: Path) -> None:
    source = db_file_path()
    if source is None or not Path(source).is_file():
        raise SystemExit("Existing SQLite database required.")
    folder.mkdir(parents=True, exist_ok=True)
    encrypted_path = folder / "bot.db.fernet"
    if encrypted_path.exists():
        raise SystemExit("Backup already exists; choose a new directory.")
    plain = Path(await make_backup_file(source))
    try:
        with sqlite3.connect(plain) as connection:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            violations = len(connection.execute("PRAGMA foreign_key_check").fetchall())
            revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]
            users = connection.execute("SELECT count(*) FROM users").fetchone()[0]
        if integrity != "ok" or violations:
            raise SystemExit("Database integrity check failed; no backup published.")
        content = plain.read_bytes()
        cipher = Fernet(settings.fernet_key.encode("ascii"))
        encrypted = cipher.encrypt(content)
        assert cipher.decrypt(encrypted) == content
        encrypted_path.write_bytes(encrypted)
        report = {"revision": revision, "users": users, "integrity": integrity,
                  "fk_violations": violations, "decrypt_verified": True,
                  "snapshot_sha256": hashlib.sha256(content).hexdigest()}
        (folder / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report))
    finally:
        plain.unlink(missing_ok=True)


if __name__ == "__main__":
    import sys
    try:
        asyncio.run(main(Path(sys.argv[1])))
    except Exception as error:
        raise SystemExit(f"Backup failed: {type(error).__name__}") from None

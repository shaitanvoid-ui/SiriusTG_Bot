from __future__ import annotations

from utils.backup_crypto import decrypt_file, encrypt_file


def test_backup_roundtrip_is_encrypted(tmp_path) -> None:
    source = tmp_path / "source.db"
    encrypted = tmp_path / "backup.db.fernet"
    restored = tmp_path / "restored.db"
    source.write_bytes(b"SQLite format 3\x00private-data")

    encrypt_file(source, encrypted)
    assert encrypted.read_bytes() != source.read_bytes()
    assert b"private-data" not in encrypted.read_bytes()

    decrypt_file(encrypted, restored)
    assert restored.read_bytes() == source.read_bytes()

"""Шифрование и локальное восстановление резервных копий SQLite."""
from __future__ import annotations

import argparse
from pathlib import Path

from core.crypto import decrypt_bytes, encrypt_bytes


def encrypt_file(source: str | Path, destination: str | Path) -> None:
    src = Path(source)
    Path(destination).write_bytes(encrypt_bytes(src.read_bytes()))


def decrypt_file(source: str | Path, destination: str | Path) -> None:
    src = Path(source)
    Path(destination).write_bytes(decrypt_bytes(src.read_bytes()))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Расшифровать SIRIUS SQLite backup с ключом FERNET_KEY"
    )
    parser.add_argument("source", help="Файл .db.fernet")
    parser.add_argument("destination", help="Куда сохранить восстановленный .db")
    args = parser.parse_args()
    decrypt_file(args.source, args.destination)


if __name__ == "__main__":
    main()

"""Create a missing Fernet key in a local dotenv file without displaying it.

Run explicitly during a new installation. Existing nonempty keys are preserved.
The helper never loads bot configuration, connects to Telegram, or opens a DB.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from cryptography.fernet import Fernet


def main(path: Path) -> None:
    source = path.read_text(encoding="utf-8-sig")
    match = re.search(r"(?m)^FERNET_KEY=([^\r\n]*)$", source)
    if match is None:
        raise SystemExit("FERNET_KEY field is missing; no changes made.")
    current = match.group(1).strip().strip("\"'")
    if current:
        try:
            Fernet(current.encode("ascii"))
        except (ValueError, UnicodeError):
            raise SystemExit("Existing key is invalid; no changes made.") from None
        print("Existing Fernet key preserved.")
        return
    key = Fernet.generate_key().decode("ascii")
    updated = source[:match.start(1)] + key + source[match.end(1):]
    path.write_text(updated, encoding="utf-8", newline="\n")
    print("Fernet key saved locally; its value is not displayed.")


if __name__ == "__main__":
    main(Path(sys.argv[1]))

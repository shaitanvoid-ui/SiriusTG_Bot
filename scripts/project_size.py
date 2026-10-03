"""Count published Python source; never traverse runtime data or dependencies."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


def count(root: Path) -> dict:
    files = subprocess.check_output(
        ["git", "ls-files", "-z", "--", "*.py"], cwd=root,
    ).decode("utf-8").split("\0")
    groups = {name: {"files": 0, "physical": 0, "nonblank": 0}
              for name in ("production", "tests", "scripts")}
    production = {"bot", "core", "db", "locales", "migrations", "ml",
                  "services", "userbot", "utils", "workers"}
    for relative in files:
        if not relative:
            continue
        path = root / relative
        first = Path(relative).parts[0]
        group = first if first in {"tests", "scripts"} else "production"
        if group == "production" and first not in production and relative != "main.py":
            continue
        if not path.is_file():
            continue
        lines = path.read_text(encoding="utf-8-sig").splitlines()
        groups[group]["files"] += 1
        groups[group]["physical"] += len(lines)
        groups[group]["nonblank"] += sum(bool(line.strip()) for line in lines)
    return {
        "method": "tracked .py only; nonblank includes comments and docstrings",
        "groups": groups,
        "total": {key: sum(values[key] for values in groups.values())
                  for key in ("files", "physical", "nonblank")},
    }


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    print(json.dumps(count(root), ensure_ascii=False, indent=2))

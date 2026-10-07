from __future__ import annotations

import re
from pathlib import Path

_ENV_KEY = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")


def read_env_map(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = _ENV_KEY.match(stripped)
        if match:
            out[match.group(1)] = match.group(2)
    return out


def write_env_updates(path: Path, updates: dict[str, str | None]) -> None:
    """Merge updates into .env. None or empty string removes the key."""
    lines: list[str] = []
    seen: set[str] = set()
    if path.is_file():
        lines = path.read_text(encoding="utf-8").splitlines()

    new_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue
        match = _ENV_KEY.match(stripped)
        if not match:
            new_lines.append(line)
            continue
        key = match.group(1)
        if key not in updates:
            new_lines.append(line)
            seen.add(key)
            continue
        value = updates[key]
        if value is None or value == "":
            seen.add(key)
            continue
        new_lines.append(f"{key}={value}")
        seen.add(key)

    for key, value in updates.items():
        if key in seen or value is None or value == "":
            continue
        new_lines.append(f"{key}={value}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(new_lines).rstrip() + "\n", encoding="utf-8")

from __future__ import annotations

import json
from pathlib import Path


def write_file_sd(path: Path, groups: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(groups, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)

"""Static AWC engine catalog from config/clusters.yaml (optional future: console API sync)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from backend.app.services.awc_catalog import build_engine_catalog  # noqa: E402


def main() -> None:
    print(json.dumps(build_engine_catalog(), indent=2))


if __name__ == "__main__":
    main()

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from backend.app.settings import settings


def load_alert_rule_groups() -> list[dict[str, Any]]:
    alerts_dir = settings.cpw_config_dir / "alerts"
    groups: list[dict[str, Any]] = []
    if not alerts_dir.is_dir():
        return groups
    for path in sorted(alerts_dir.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        groups.extend(raw.get("groups") or [])
    return groups


async def sync_alert_definitions() -> dict[str, Any]:
    """Return config-driven alert groups (Grafana provisioning hook in deploy/grafana/provisioning)."""
    groups = load_alert_rule_groups()
    provisioning_dir = settings.cpw_config_dir.parent / "deploy/grafana/provisioning/alerting"
    provisioning_dir.mkdir(parents=True, exist_ok=True)
    out = provisioning_dir / "cpw-rules.yaml"
    out.write_text(yaml.safe_dump({"groups": groups}), encoding="utf-8")
    return {"groups": len(groups), "written_to": str(out)}

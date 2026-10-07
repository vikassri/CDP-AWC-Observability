from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from backend.app.settings import settings


class AlertRule(BaseModel):
    rule_id: str
    group: str
    alert: str
    expr: str
    for_duration: str = Field(default="0m", alias="for")
    labels: dict[str, str] = Field(default_factory=dict)
    annotations: dict[str, str] = Field(default_factory=dict)
    product: str = ""

    model_config = {"populate_by_name": True}


def _slug(rule_id: str) -> str:
    return rule_id.replace(" ", "_")


def load_alert_rules() -> list[AlertRule]:
    alerts_dir = settings.cpw_config_dir / "alerts"
    rules: list[AlertRule] = []
    if not alerts_dir.is_dir():
        return rules
    for path in sorted(alerts_dir.glob("*.yaml")):
        if path.name == "assignments.yaml":
            continue
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for group in raw.get("groups") or []:
            group_name = group.get("name") or path.stem
            for item in group.get("rules") or []:
                alert_name = item.get("alert") or "Unnamed"
                rule_id = _slug(f"{group_name}_{alert_name}")
                labels = {str(k): str(v) for k, v in (item.get("labels") or {}).items()}
                product = labels.get("product") or path.stem.replace("_hub", "")
                rules.append(
                    AlertRule(
                        rule_id=rule_id,
                        group=group_name,
                        alert=alert_name,
                        expr=item.get("expr") or "vector(0)",
                        for_duration=item.get("for") or "0m",
                        labels=labels,
                        annotations={
                            str(k): str(v) for k, v in (item.get("annotations") or {}).items()
                        },
                        product=product,
                    )
                )
    return rules


def append_custom_alert_rule(
    *,
    alert: str,
    expr: str,
    product: str,
    severity: str = "warning",
    summary: str = "",
    for_duration: str = "5m",
) -> AlertRule:
    alerts_dir = settings.cpw_config_dir / "alerts"
    path = alerts_dir / "custom.yaml"
    alerts_dir.mkdir(parents=True, exist_ok=True)
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) if path.is_file() else {"groups": []}
    groups = raw.get("groups") or []
    custom_group = next((g for g in groups if g.get("name") == "custom_ui"), None)
    if not custom_group:
        custom_group = {"name": "custom_ui", "rules": []}
        groups.append(custom_group)
    rule_doc = {
        "alert": alert,
        "expr": expr,
        "for": for_duration,
        "labels": {"severity": severity, "product": product},
        "annotations": {"summary": summary or alert},
    }
    custom_group.setdefault("rules", []).append(rule_doc)
    path.write_text(yaml.safe_dump({"groups": groups}, sort_keys=False), encoding="utf-8")
    rule_id = _slug(f"custom_ui_{alert}")
    return AlertRule(
        rule_id=rule_id,
        group="custom_ui",
        alert=alert,
        expr=expr,
        for_duration=for_duration,
        labels={"severity": severity, "product": product},
        annotations={"summary": summary or alert},
        product=product,
    )


def load_default_assignments() -> dict[str, Any]:
    path = settings.cpw_config_dir / "alerts" / "assignments.yaml"
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}

from __future__ import annotations

from functools import lru_cache
from typing import Any

import yaml

from backend.app.settings import settings


@lru_cache
def _load_raw() -> dict[str, Any]:
    path = settings.cpw_config_dir / "metrics_catalog.yaml"
    if not path.is_file():
        return {"charts": [], "job_status": []}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_chart_catalog() -> list[dict[str, str]]:
    charts: list[dict[str, str]] = []
    for item in _load_raw().get("charts") or []:
        charts.append(
            {
                "product": str(item.get("product", "")),
                "title": str(item.get("title", "")),
                "query": str(item.get("query", "")),
            }
        )
    return charts


def load_job_status_defs(product: str | None = None) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for item in _load_raw().get("job_status") or []:
        if product and item.get("product") != product:
            continue
        out.append(
            {
                "product": str(item.get("product", "")),
                "key": str(item.get("key", "")),
                "label": str(item.get("label", "")),
                "query": str(item.get("query", "")),
                "unit": str(item.get("unit") or ""),
            }
        )
    return out


def substitute_cluster(promql: str, cluster_id: str) -> str:
    return promql.replace("$cluster", cluster_id)

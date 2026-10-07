from __future__ import annotations

import asyncio
from typing import Any

from backend.app.config_loader import load_clusters
from backend.app.services.metrics_catalog import load_job_status_defs
from backend.app.services.promql_helpers import apply_cluster_label, normalize_promql
from backend.app.services.prometheus_client import query_prometheus


def _round_job_value(value: float | None, unit: str | None) -> float | None:
    if value is None:
        return None
    if unit == "percent":
        return round(value, 2)
    return value


def _scalar_from_result(payload: dict[str, Any]) -> float | None:
    data = payload.get("data") or {}
    if data.get("resultType") != "vector":
        return None
    results = data.get("result") or []
    if not results:
        return 0.0
    total = 0.0
    for series in results:
        value = series.get("value")
        if value and len(value) >= 2:
            try:
                total += float(value[1])
            except (TypeError, ValueError):
                continue
    return total


async def job_status_for_cluster(cluster_id: str, product: str | None = None) -> dict[str, Any]:
    cluster = next((c for c in load_clusters() if c.id == cluster_id), None)
    if not cluster:
        return {"cluster_id": cluster_id, "error": "unknown cluster", "items": []}

    prod = product or cluster.product
    defs = load_job_status_defs(prod)

    async def one(definition: dict[str, str]) -> dict[str, Any]:
        promql = normalize_promql(apply_cluster_label(definition["query"], cluster_id))
        value: float | None = None
        error: str | None = None
        try:
            result = await query_prometheus(promql)
            value = _round_job_value(
                _scalar_from_result(result), definition.get("unit") or None
            )
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
            return {
                "key": definition["key"],
                "label": definition["label"],
                "value": value,
                "unit": definition.get("unit") or None,
                "error": error,
                "prom_ok": False,
            }
        return {
            "key": definition["key"],
            "label": definition["label"],
            "value": value,
            "unit": definition.get("unit") or None,
            "error": error,
            "prom_ok": True,
        }

    gathered = await asyncio.gather(*[one(d) for d in defs])
    prom_ok = all(item.get("prom_ok", True) for item in gathered)
    for item in gathered:
        item.pop("prom_ok", None)
    items = gathered

    return {
        "cluster_id": cluster_id,
        "product": prod,
        "prometheus_available": prom_ok,
        "items": items,
    }


async def job_status_fleet() -> dict[str, Any]:
    clusters = [
        c for c in load_clusters() if c.product not in ("cai", "polaris")
    ]

    snapshots = await asyncio.gather(
        *[job_status_for_cluster(c.id, c.product) for c in clusters]
    )
    by_product: dict[str, list[dict]] = {}
    for cluster, snapshot in zip(clusters, snapshots, strict=True):
        by_product.setdefault(cluster.product, []).append(snapshot)
    return {"products": by_product}

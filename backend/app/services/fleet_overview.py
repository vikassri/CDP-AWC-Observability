from __future__ import annotations

import asyncio
from typing import Any

from backend.app.config_loader import load_clusters
from backend.app.services.service_overview import product_overview

_FLEET_PRODUCTS = ("nifi", "spark", "trino", "flink", "airflow")


def _primary_cluster_id(product: str) -> str | None:
    for cluster in load_clusters():
        if cluster.product == product:
            return cluster.id
    return None


def _summarize_overview(product: str, payload: dict[str, Any]) -> dict[str, Any]:
    deployments = payload.get("deployments") or []
    deployment_count = payload.get("deployment_count", len(deployments))
    healthy = payload.get("healthy_count")
    if healthy is None:
        healthy = sum(1 for d in deployments if d.get("status") == "healthy")
    with_issues = payload.get("with_issues_count")
    if with_issues is None:
        with_issues = sum(1 for d in deployments if d.get("status") != "healthy")
    rows = []
    for dep in deployments[:12]:
        if not isinstance(dep, dict):
            continue
        issues = dep.get("issues") or []
        rows.append(
            {
                "name": dep.get("name"),
                "namespace": dep.get("namespace"),
                "status": dep.get("status"),
                "issue_preview": issues[0] if issues else None,
            }
        )
    return {
        "product": product,
        "cluster_id": payload.get("cluster_id"),
        "display_name": payload.get("display_name"),
        "deployment_count": deployment_count,
        "healthy_count": healthy,
        "with_issues_count": with_issues,
        "error": payload.get("error"),
        "deployments": rows,
    }


async def fleet_deployment_overview() -> dict[str, Any]:
    from backend.app.services.overview_cache import get_cached, set_cached
    from backend.app.settings import settings

    fleet_cache_key = "fleet:deployment_overview"
    cached = get_cached(fleet_cache_key, settings.cpw_overview_cache_sec * 2)
    if cached:
        return cached

    pairs = [(p, _primary_cluster_id(p)) for p in _FLEET_PRODUCTS]
    valid = [(p, cid) for p, cid in pairs if cid]

    async def one(product: str, cluster_id: str) -> tuple[str, dict[str, Any]]:
        try:
            raw = await product_overview(product, cluster_id, lite=True)
        except Exception as exc:  # noqa: BLE001
            raw = {
                "product": product,
                "cluster_id": cluster_id,
                "error": str(exc),
                "deployments": [],
            }
        return product, _summarize_overview(product, raw)

    results = await asyncio.gather(*[one(p, cid) for p, cid in valid])
    by_product = {product: summary for product, summary in results}
    for product, _cid in pairs:
        if product not in by_product:
            by_product[product] = {
                "product": product,
                "cluster_id": None,
                "display_name": None,
                "deployment_count": 0,
                "healthy_count": 0,
                "with_issues_count": 0,
                "error": "no cluster registered",
                "deployments": [],
            }
    total_deployments = sum(s.get("deployment_count") or 0 for s in by_product.values())
    total_issues = sum(s.get("with_issues_count") or 0 for s in by_product.values())
    result = {
        "products": by_product,
        "totals": {
            "deployments": total_deployments,
            "with_issues": total_issues,
        },
        "refetch_hint_sec": 4,
    }
    set_cached(fleet_cache_key, result)
    return result

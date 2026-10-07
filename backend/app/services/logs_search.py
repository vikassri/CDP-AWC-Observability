from __future__ import annotations

from typing import Any

import httpx

from backend.app.schemas import LogSearchIn
from backend.app.settings import settings


async def search_logs(params: LogSearchIn) -> dict[str, Any]:
    must: list[dict[str, Any]] = [{"query_string": {"query": params.q or "*"}}]
    if params.cluster:
        must.append({"term": {"cluster.keyword": params.cluster}})
    if params.product:
        must.append({"term": {"product.keyword": params.product}})
    if params.namespace:
        must.append({"term": {"k8s.namespace.name.keyword": params.namespace}})
    if params.pod:
        must.append({"term": {"k8s.pod.name.keyword": params.pod}})

    body = {
        "size": min(params.size, 200),
        "query": {"bool": {"must": must}},
        "sort": [{"@timestamp": {"order": "desc"}}],
    }
    url = f"{settings.cpw_opensearch_url.rstrip('/')}/cpw-logs/_search"
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(url, json=body)
            if resp.status_code == 404:
                return {"hits": [], "message": "Index cpw-logs not ready yet"}
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as exc:
            return {"hits": [], "message": str(exc)}

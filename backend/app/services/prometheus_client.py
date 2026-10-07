from __future__ import annotations

from typing import Any

import httpx

from backend.app.settings import settings


async def query_prometheus(query: str, time: str | None = None) -> dict[str, Any]:
    params: dict[str, str] = {"query": query}
    if time:
        params["time"] = time
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{settings.cpw_prometheus_url}/api/v1/query", params=params)
        resp.raise_for_status()
        return resp.json()


async def query_range_prometheus(
    query: str,
    start: float,
    end: float,
    step: str = "60s",
) -> dict[str, Any]:
    params = {"query": query, "start": str(start), "end": str(end), "step": step}
    async with httpx.AsyncClient(timeout=45.0) as client:
        resp = await client.get(f"{settings.cpw_prometheus_url}/api/v1/query_range", params=params)
        resp.raise_for_status()
        return resp.json()

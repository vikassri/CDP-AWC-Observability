from __future__ import annotations

from typing import Any

from collectors.discovery.fleet_workloads import discover_fleet, discover_for_cluster


async def workloads_for_cluster(cluster_id: str) -> dict[str, Any]:
    import asyncio

    return await asyncio.to_thread(discover_for_cluster, cluster_id)


async def workloads_fleet() -> list[dict[str, Any]]:
    import asyncio

    return await asyncio.to_thread(discover_fleet)

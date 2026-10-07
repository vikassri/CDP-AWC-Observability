from __future__ import annotations

from fastapi import APIRouter

from backend.app.config_loader import load_clusters, resolve_kubeconfig
from backend.app.services.awc_catalog import engine_console_url, fleet_console_url
from backend.app.schemas import ClusterHealthOut, ClusterOut, EngineOut
from backend.app.services.k8s_pool import check_cluster_health
from backend.app.services.workload_discovery import workloads_fleet, workloads_for_cluster

router = APIRouter(prefix="/clusters", tags=["clusters"])


@router.get("", response_model=list[ClusterOut])
async def list_clusters() -> list[ClusterOut]:
    out: list[ClusterOut] = []
    for c in load_clusters():
        url = engine_console_url(c)
        kc = resolve_kubeconfig(c)
        out.append(
            ClusterOut(
                id=c.id,
                display_name=c.display_name,
                product=c.product,
                context=c.context,
                collectors=c.collectors,
                awc_console_url=url,
                kubeconfig_ref=c.kubeconfig,
                kubeconfig_present=kc.is_file(),
                awc_engine_id=c.awc_engine_id or c.id,
                services=[c.product],
            )
        )
    return out


@router.get("/{cluster_id}/workloads")
async def cluster_workloads(cluster_id: str) -> dict:
    """kubectl discovery: deployments, apps, pods, and how metrics/logs are collected."""
    return await workloads_for_cluster(cluster_id)


@router.get("/workloads/fleet")
async def fleet_workloads() -> dict:
    snapshots = await workloads_fleet()
    return {"clusters": snapshots}


@router.get("/{cluster_id}/health", response_model=ClusterHealthOut)
async def cluster_health(cluster_id: str) -> ClusterHealthOut:
    for c in load_clusters():
        if c.id != cluster_id:
            continue
        kc = resolve_kubeconfig(c)
        result = await check_cluster_health(kc, c.context)
        return ClusterHealthOut(id=c.id, healthy=bool(result["healthy"]), message=str(result["message"]))
    return ClusterHealthOut(id=cluster_id, healthy=False, message="Unknown cluster")


@router.get("/engines/all", response_model=list[EngineOut])
async def list_engines_legacy() -> list[EngineOut]:
    return await list_engines()


router_engines = APIRouter(prefix="/engines", tags=["engines"])


@router_engines.get("", response_model=list[EngineOut])
async def list_engines() -> list[EngineOut]:
    engines: list[EngineOut] = []
    for c in load_clusters():
        engines.append(
            EngineOut(
                id=c.awc_engine_id or c.id,
                display_name=c.display_name,
                product=c.product,
                cluster_id=c.id,
                awc_console_url=engine_console_url(c),
                collectors=c.collectors,
            )
        )
    return engines


@router_engines.get("/fleet-url")
async def engines_fleet_url() -> dict[str, str]:
    return {"fleet_console_url": fleet_console_url()}

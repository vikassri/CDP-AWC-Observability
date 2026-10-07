from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

from backend.app.config_loader import load_clusters, resolve_kubeconfig
from backend.app.services.nifi_overview import nifi_overview
from backend.app.services.overview_cache import (
    get_cached,
    merge_logs_from_previous,
    refresh_logs_this_cycle,
    set_cached,
)
from backend.app.settings import settings
from backend.app.services.overview_common import (
    finalize_status,
    logs_for_workload,
    prom_scalar_cluster,
)

_LEGACY = Path(__file__).resolve().parents[2] / "collectors" / "legacy"
if str(_LEGACY) not in sys.path:
    sys.path.insert(0, str(_LEGACY))


async def _spark_overview(
    cluster_id: str,
    kc: Path,
    *,
    refresh_logs: bool,
    lite: bool = False,
) -> list[dict[str, Any]]:
    from spark_discovery import discover_applications, discover_log_pods  # type: ignore[import-not-found]

    apps = await asyncio.to_thread(discover_applications, cluster_id, kc)
    if lite:
        rows: list[dict[str, Any]] = []
        failed_count = 0
        for app in apps:
            state = str(app.state)
            if "fail" not in state.lower():
                continue
            failed_count += 1
            status, issues = finalize_status([f"Application state: {state}"])
            rows.append(
                {
                    "name": app.name,
                    "namespace": app.namespace,
                    "status": status,
                    "issues": issues,
                    "detail": {"state": state, "workspace": app.workspace},
                    "metrics": {},
                    "logs": {"source": "skipped", "lines": [], "flagged": [], "scanned_pod": None},
                }
            )
        return rows, len(apps), failed_count

    pods = await asyncio.to_thread(discover_log_pods, cluster_id, kc)

    async def build_app_row(app: Any) -> dict[str, Any]:
        issues: list[str] = []
        state = str(app.state)
        if "fail" in state.lower():
            issues.append(f"Application state: {state}")
        driver = next((p for p in pods if p.spark_app == app.name and p.role == "driver"), None)
        log_pod = driver.pod if driver else (pods[0].pod if pods else "")
        metrics = {
            "failed_flag": await prom_scalar_cluster(
                'max(spark_application_failed{cluster="$cluster", spark_namespace="$ns", spark_application="$app"})',
                cluster_id,
                ns=app.namespace,
                app=app.name,
            ),
            "apps_in_state": await prom_scalar_cluster(
                'sum(spark_applications_total{cluster="$cluster", spark_namespace="$ns", state="$state"})',
                cluster_id,
                ns=app.namespace,
                state=state,
            ),
        }
        logs = (
            await logs_for_workload(
                cluster_id=cluster_id,
                product="spark",
                namespace=app.namespace,
                kubeconfig=kc,
                pod=log_pod,
            )
            if refresh_logs
            else {"source": "cached", "lines": [], "flagged": [], "scanned_pod": log_pod}
        )
        if logs["flagged"]:
            issues.append(f"{len(logs['flagged'])} error line(s) in logs")
        status, issues = finalize_status(issues)
        return {
            "name": app.name,
            "namespace": app.namespace,
            "status": status,
            "issues": issues,
            "detail": {"state": state, "workspace": app.workspace},
            "metrics": metrics,
            "logs": logs,
        }

    return list(await asyncio.gather(*[build_app_row(app) for app in apps]))


async def _trino_overview(
    cluster_id: str, kc: Path, *, refresh_logs: bool, lite: bool = False
) -> list[dict[str, Any]]:
    from trino_discovery import discover_in_cluster  # type: ignore[import-not-found]

    targets = await asyncio.to_thread(discover_in_cluster, cluster_id, kc)
    by_engine: dict[tuple[str, str], list] = {}
    for t in targets:
        by_engine.setdefault((t.namespace, t.trino_name), []).append(t)

    rows: list[dict[str, Any]] = []
    for (namespace, trino_name), group in sorted(by_engine.items()):
        issues: list[str] = []
        if not any(t.trino_ready for t in group):
            issues.append("Trino CR not Ready")
        coord = next((t for t in group if t.role == "coordinator"), group[0])
        metrics = {
            "engine_ready": await prom_scalar_cluster(
                'max(trino_engine_ready{cluster="$cluster", trino_namespace="$ns", trino_instance="$inst"})',
                cluster_id,
                ns=namespace,
                inst=trino_name,
            ),
            "nodes_up": await prom_scalar_cluster(
                'sum(trino_node_up{cluster="$cluster", trino_namespace="$ns", trino_instance="$inst"})',
                cluster_id,
                ns=namespace,
                inst=trino_name,
            ),
        }
        if metrics["engine_ready"] is not None and metrics["engine_ready"] < 1:
            issues.append("Engine readiness metric below 1")
        if lite:
            logs = {"source": "skipped", "lines": [], "flagged": [], "scanned_pod": coord.pod}
        else:
            logs = (
                await logs_for_workload(
                    cluster_id=cluster_id,
                    product="trino",
                    namespace=namespace,
                    kubeconfig=kc,
                    pod=coord.pod,
                )
                if refresh_logs
                else {"source": "cached", "lines": [], "flagged": [], "scanned_pod": coord.pod}
            )
            if logs["flagged"]:
                issues.append(f"{len(logs['flagged'])} error line(s) in coordinator logs")
        status, issues = finalize_status(issues)
        rows.append(
            {
                "name": trino_name,
                "namespace": namespace,
                "status": status,
                "issues": issues,
                "detail": {"pods": len(group)},
                "metrics": metrics,
                "logs": logs,
            }
        )
    return rows


async def _flink_overview(
    cluster_id: str, kc: Path, *, refresh_logs: bool, lite: bool = False
) -> list[dict[str, Any]]:
    from flink_discovery import discover_deployments, discover_session_jobs  # type: ignore[import-not-found]

    deps = await asyncio.to_thread(discover_deployments, cluster_id, kc)
    jobs = await asyncio.to_thread(discover_session_jobs, cluster_id, kc)
    rows: list[dict[str, Any]] = []

    async def add_row(name: str, namespace: str, job_state: str, kind: str) -> dict[str, Any]:
        issues: list[str] = []
        if job_state.upper() in ("FAILED", "FAILING"):
            issues.append(f"Job state: {job_state}")
        metrics = (
            {}
            if lite
            else {
                "deployments": await prom_scalar_cluster(
                    'sum(flink_deployments_total{cluster="$cluster", flink_namespace="$ns", job_state="$st"})',
                    cluster_id,
                    ns=namespace,
                    st=job_state.upper(),
                ),
            }
        )
        if lite:
            logs = {"source": "skipped", "lines": [], "flagged": [], "scanned_pod": None}
        else:
            logs = (
                await logs_for_workload(
                    cluster_id=cluster_id,
                    product="flink",
                    namespace=namespace,
                    kubeconfig=kc,
                    pod="",
                )
                if refresh_logs
                else {"source": "cached", "lines": [], "flagged": [], "scanned_pod": None}
            )
        status, issues = finalize_status(issues)
        return {
            "name": name,
            "namespace": namespace,
            "status": status,
            "issues": issues,
            "detail": {"kind": kind, "job_state": job_state},
            "metrics": metrics,
            "logs": logs,
        }

    built = await asyncio.gather(
        *[add_row(d.name, d.namespace, d.job_state, "FlinkDeployment") for d in deps],
        *[add_row(j.name, j.namespace, j.job_state, "SessionJob") for j in jobs],
    )
    return list(built)


async def _airflow_overview(
    cluster_id: str, kc: Path, *, refresh_logs: bool, lite: bool = False
) -> list[dict[str, Any]]:
    from airflow_discovery import discover_in_cluster  # type: ignore[import-not-found]

    targets = await asyncio.to_thread(discover_in_cluster, cluster_id, kc)
    by_release: dict[tuple[str, str], list] = {}
    for t in targets:
        by_release.setdefault((t.namespace, t.release), []).append(t)

    rows: list[dict[str, Any]] = []
    for (namespace, release), group in sorted(by_release.items()):
        issues: list[str] = []
        components = {t.component for t in group}
        if "scheduler" not in components:
            issues.append("Scheduler pod not found")
        scan_pod = next((t.pod for t in group if t.component == "scheduler"), group[0].pod)
        metrics = (
            {"pods_up": float(len(group))}
            if lite
            else {
                "pods_up": float(len(group)),
                "failed_dag_runs": await prom_scalar_cluster(
                    'sum(airflow_dagrun_finished_total{cluster="$cluster", state=~"(?i)failed"})',
                    cluster_id,
                ),
            }
        )
        if lite:
            logs = {"source": "skipped", "lines": [], "flagged": [], "scanned_pod": scan_pod}
        else:
            logs = (
                await logs_for_workload(
                    cluster_id=cluster_id,
                    product="airflow",
                    namespace=namespace,
                    kubeconfig=kc,
                    pod=scan_pod,
                )
                if refresh_logs
                else {"source": "cached", "lines": [], "flagged": [], "scanned_pod": scan_pod}
            )
            if logs["flagged"]:
                issues.append(f"{len(logs['flagged'])} error line(s) in logs")
        status, issues = finalize_status(issues)
        rows.append(
            {
                "name": release,
                "namespace": namespace,
                "status": status,
                "issues": issues,
                "detail": {"components": sorted(components)},
                "metrics": metrics,
                "logs": logs,
            }
        )
    return rows


async def product_overview(product: str, cluster_id: str, *, lite: bool = False) -> dict[str, Any]:
    product = product.lower()
    cache_key = f"{product}:{cluster_id}:lite" if lite else f"{product}:{cluster_id}"
    cache_ttl = settings.cpw_overview_cache_sec * (2.5 if lite else 1.0)
    cached = get_cached(cache_key, cache_ttl)
    if cached:
        return cached

    refresh_logs = False if lite else refresh_logs_this_cycle()

    if product == "nifi":
        raw = await nifi_overview(cluster_id, refresh_logs=refresh_logs)
        result = {
            "product": "nifi",
            "cluster_id": raw.get("cluster_id"),
            "display_name": raw.get("display_name"),
            "deployments": raw.get("deployments") or [],
            "deployment_count": raw.get("deployment_count", 0),
            "refetch_hint_sec": 2,
        }
        if not refresh_logs:
            result = merge_logs_from_previous(cache_key, result)
        set_cached(cache_key, result)
        return result

    cluster = next((c for c in load_clusters() if c.id == cluster_id), None)
    if not cluster:
        return {"product": product, "cluster_id": cluster_id, "error": "unknown cluster", "deployments": []}
    if cluster.product != product:
        return {
            "product": product,
            "cluster_id": cluster_id,
            "error": f"cluster {cluster_id} is product {cluster.product}",
            "deployments": [],
        }
    kc = resolve_kubeconfig(cluster)
    if not kc.is_file():
        return {"product": product, "cluster_id": cluster_id, "error": "kubeconfig missing", "deployments": []}

    builders = {
        "spark": _spark_overview,
        "trino": _trino_overview,
        "flink": _flink_overview,
        "airflow": _airflow_overview,
    }
    builder = builders.get(product)
    if not builder:
        return {"product": product, "cluster_id": cluster_id, "deployments": [], "error": "unsupported product"}

    built = await builder(cluster_id, kc, refresh_logs=refresh_logs, lite=lite)
    deployment_count: int
    deployments: list[dict[str, Any]]
    if lite and product == "spark" and isinstance(built, tuple):
        deployments, deployment_count, with_issues_count = built
    else:
        deployments = built  # type: ignore[assignment]
        deployment_count = len(deployments)
        with_issues_count = sum(1 for d in deployments if d.get("status") != "healthy")
    result = {
        "product": product,
        "cluster_id": cluster_id,
        "display_name": cluster.display_name,
        "deployment_count": deployment_count,
        "healthy_count": max(deployment_count - with_issues_count, 0),
        "with_issues_count": with_issues_count,
        "deployments": deployments,
        "refetch_hint_sec": 4 if lite else 2,
    }
    if not refresh_logs:
        result = merge_logs_from_previous(cache_key, result)
    set_cached(cache_key, result)
    return result

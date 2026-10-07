from __future__ import annotations

import asyncio
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from backend.app.config_loader import load_clusters, resolve_kubeconfig
from backend.app.services.logs_search import search_logs
from backend.app.services.prometheus_client import query_prometheus
from backend.app.services.promql_helpers import apply_cluster_label
from backend.app.schemas import LogSearchIn

_LEGACY = Path(__file__).resolve().parents[2] / "collectors" / "legacy"

_PER_DEPLOYMENT_METRICS: list[tuple[str, str]] = [
    (
        "deployed_flows",
        'count(nifi_amount_threads_active{cluster="$cluster", nifi_namespace="$ns", component_type="RootProcessGroup"})',
    ),
    (
        "memory_usage_pct",
        'max(nifi_jvm_heap_usage{cluster="$cluster", nifi_namespace="$ns"}) * 100',
    ),
    ("exporter_up", 'max(nifi_status_exporter_up{cluster="$cluster", nifi_namespace="$ns"})'),
    (
        "bulletins_error",
        'count(nifi_bulletin{cluster="$cluster", nifi_namespace="$ns", level=~"(?i)ERROR|FATAL"})',
    ),
    (
        "bulletins_warn",
        'count(nifi_bulletin{cluster="$cluster", nifi_namespace="$ns", level=~"(?i)WARNING|WARN"})',
    ),
]

_ERROR_LINE = re.compile(r"(?i)(error|exception|failed|fatal)")
_BULLETIN_MARKER = re.compile(r"(?i)bulletin|bulletinlevel|nifi\.bulletin")
_BULLETIN_SEVERE = re.compile(r"(?i)(\[ERROR\]|\[FATAL\]|level[=:]\s*ERROR|Bulletin.*ERROR)")


def _analyze_app_log_lines(lines: list[str]) -> tuple[list[str], list[str]]:
    """Split app-log / OpenSearch lines into bulletin lines and other error lines."""
    flagged: list[str] = []
    bulletins: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        is_bulletin = bool(_BULLETIN_MARKER.search(stripped))
        if is_bulletin:
            bulletins.append(stripped)
            if _BULLETIN_SEVERE.search(stripped):
                flagged.append(stripped)
            continue
        if _ERROR_LINE.search(stripped):
            flagged.append(stripped)
    return flagged, bulletins


async def _prom_scalar(promql: str, *, missing_is_none: bool = False) -> float | None:
    try:
        payload = await query_prometheus(promql)
    except Exception:  # noqa: BLE001
        return None
    data = payload.get("data") or {}
    if data.get("resultType") != "vector":
        return None
    results = data.get("result") or []
    if not results:
        return None if missing_is_none else 0.0
    total = 0.0
    for series in results:
        value = series.get("value")
        if value and len(value) >= 2:
            try:
                total += float(value[1])
            except (TypeError, ValueError):
                continue
    return total


def _discover_nifi(cluster_id: str, kubeconfig: Path) -> list[dict[str, Any]]:
    import sys

    legacy = str(_LEGACY)
    if legacy not in sys.path:
        sys.path.insert(0, legacy)
    from nifi_discovery import assign_ports, discover_in_cluster  # type: ignore[import-not-found]

    deps = assign_ports(discover_in_cluster(cluster_id, kubeconfig))
    return [asdict(d) for d in deps if d.has_prometheus]


async def _kubectl_log_tail(
    kubeconfig: Path,
    namespace: str,
    pod: str,
    *,
    tail: int = 120,
) -> list[str]:
    # CDF NiFi ships nifi-app.log via the app-log sidecar (see uob_poc PROJECT.md §3.3).
    for container in ("app-log", None):
        args = [
            "kubectl",
            f"--kubeconfig={kubeconfig}",
            "logs",
            pod,
            "-n",
            namespace,
            f"--tail={tail}",
        ]
        if container:
            args.extend(["-c", container])
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _stderr = await asyncio.wait_for(proc.communicate(), timeout=45)
        if proc.returncode == 0 and stdout:
            return stdout.decode(errors="replace").splitlines()
    return []


async def _logs_for_deployment(
    cluster_id: str,
    namespace: str,
    pods: tuple[str, ...] | list[str],
    kubeconfig: Path,
) -> dict[str, Any]:
    os_hits = await search_logs(
        LogSearchIn(
            cluster=cluster_id,
            product="nifi",
            namespace=namespace,
            q="ERROR OR bulletin OR exception OR failed",
            size=40,
        )
    )
    os_lines: list[str] = []
    raw_hits = os_hits.get("hits")
    if isinstance(raw_hits, dict):
        hit_list = raw_hits.get("hits") or []
    elif isinstance(raw_hits, list):
        hit_list = raw_hits
    else:
        hit_list = []
    for hit in hit_list:
        src = hit.get("_source") or {}
        body = src.get("body") or src.get("message") or ""
        if body:
            os_lines.append(str(body).strip())

    kubectl_lines: list[str] = []
    scan_pod = ""
    for pod in pods or []:
        lines = await _kubectl_log_tail(kubeconfig, namespace, str(pod))
        if lines:
            kubectl_lines = lines
            scan_pod = str(pod)
            break
    if not scan_pod and pods:
        scan_pod = str(pods[0])

    combined = os_lines if os_lines else kubectl_lines
    scan_pool = list(dict.fromkeys([*os_lines, *kubectl_lines]))
    flagged, bulletins = _analyze_app_log_lines(scan_pool)
    source = "none"
    if os_lines and kubectl_lines:
        source = "opensearch+kubectl"
    elif os_lines:
        source = "opensearch"
    elif kubectl_lines:
        source = "kubectl-app-log"
    return {
        "source": source,
        "lines": combined[:30],
        "flagged": flagged[:15],
        "bulletins": bulletins[:15],
        "scanned_pod": scan_pod or None,
    }


async def _pod_readiness(kubeconfig: Path, namespace: str, pods: list[str]) -> dict[str, Any]:
    if not pods:
        return {"ready": 0, "total": 0, "issues": ["No NiFi pods discovered in namespace"]}
    proc = await asyncio.create_subprocess_exec(
        "kubectl",
        f"--kubeconfig={kubeconfig}",
        "get",
        "pods",
        "-n",
        namespace,
        "-o",
        "json",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _stderr = await asyncio.wait_for(proc.communicate(), timeout=45)
    if proc.returncode != 0:
        return {"ready": 0, "total": len(pods), "issues": ["Failed to read pod status from API"]}
    import json

    items = json.loads(stdout.decode()).get("items") or []
    issues: list[str] = []
    ready = 0
    total = len(items) if items else len(pods)
    for item in items:
        name = item["metadata"]["name"]
        phase = (item.get("status") or {}).get("phase", "Unknown")
        statuses = (item.get("status") or {}).get("containerStatuses") or []
        is_ready = statuses and all(c.get("ready") for c in statuses)
        if phase == "Running" and is_ready:
            ready += 1
        else:
            issues.append(f"Pod {name} is {phase}{'' if is_ready else ' (not ready)'}")
    return {"ready": ready, "total": total, "issues": issues}


def _has_federated_metrics(metrics: dict[str, float | None]) -> bool:
    if metrics.get("exporter_up") == 1:
        return True
    for key in ("deployed_flows", "memory_usage_pct"):
        val = metrics.get(key)
        if val is not None and val > 0:
            return True
    for key in ("flowfiles_queued", "processors_running"):
        val = metrics.get(key)
        if val is not None and val > 0:
            return True
    return False


def _assess_deployment(
    *,
    has_prometheus: bool,
    local_port: int | None,
    metrics: dict[str, float | None],
    logs: dict[str, Any],
    pod_health: dict[str, Any],
) -> tuple[str, list[str]]:
    issues: list[str] = list(pod_health.get("issues") or [])
    federated = _has_federated_metrics(metrics)
    if not has_prometheus:
        issues.append("In-cluster Prometheus service not found (metrics federation unavailable)")
    elif not local_port and not federated:
        issues.append(
            "NiFi metrics port-forward not active on CAO hub — start the nifi_metrics collector "
            "(VPN/kubeconfig required) so Prometheus can federate this namespace"
        )

    memory_pct = metrics.get("memory_usage_pct")
    if memory_pct is not None and memory_pct >= 90:
        issues.append(f"High JVM heap usage ({memory_pct:.2f}%)")

    bulletin_errors = metrics.get("bulletins_error")
    if bulletin_errors is not None and bulletin_errors > 0:
        issues.append(f"{int(bulletin_errors)} NiFi ERROR bulletin(s) (Prometheus)")
    bulletin_warn = metrics.get("bulletins_warn")
    if bulletin_warn is not None and bulletin_warn >= 10:
        issues.append(f"{int(bulletin_warn)} NiFi WARNING bulletin(s) (Prometheus)")

    exporter = metrics.get("exporter_up")
    # Status exporter is optional (processor run-state only); do not flag when DFX federated metrics exist.
    if (
        exporter is not None
        and exporter < 1
        and not _has_federated_metrics(metrics)
    ):
        issues.append("NiFi status exporter not reporting for this namespace")

    log_bulletins = logs.get("bulletins") or []
    if log_bulletins:
        severe = [line for line in log_bulletins if _BULLETIN_SEVERE.search(line)]
        if severe:
            issues.append(f"{len(severe)} ERROR bulletin line(s) in app-log")
        elif len(log_bulletins) >= 5:
            issues.append(f"{len(log_bulletins)} bulletin line(s) in recent app-log")

    flagged = logs.get("flagged") or []
    non_bulletin_errors = [
        line for line in flagged if not _BULLETIN_MARKER.search(line)
    ]
    if non_bulletin_errors:
        issues.append(f"{len(non_bulletin_errors)} error line(s) in app-log")

    if any("not ready" in i.lower() or i.startswith("Pod") for i in issues[:3]):
        status = "critical"
    elif issues:
        status = "degraded"
    else:
        status = "healthy"
    return status, issues


async def _metrics_for_deployment(cluster_id: str, namespace: str) -> dict[str, float | None]:
    async def one(key: str, template: str) -> tuple[str, float | None]:
        promql = apply_cluster_label(template.replace("$ns", namespace), cluster_id)
        missing_is_none = key == "exporter_up"
        return key, await _prom_scalar(promql, missing_is_none=missing_is_none)

    pairs = await asyncio.gather(
        *[one(key, template) for key, template in _PER_DEPLOYMENT_METRICS]
    )
    return dict(pairs)


async def nifi_overview(cluster_id: str = "cdf", *, refresh_logs: bool = True) -> dict[str, Any]:
    cluster = next((c for c in load_clusters() if c.id == cluster_id), None)
    if not cluster:
        return {"cluster_id": cluster_id, "error": "unknown cluster", "deployments": []}
    if cluster.product != "nifi":
        return {
            "cluster_id": cluster_id,
            "error": f"cluster product is {cluster.product}, not nifi",
            "deployments": [],
        }

    kc = resolve_kubeconfig(cluster)
    if not kc.is_file():
        return {"cluster_id": cluster_id, "error": "kubeconfig missing", "deployments": []}

    raw_deps = await asyncio.to_thread(_discover_nifi, cluster_id, kc)

    async def build_row(dep: dict[str, Any]) -> dict[str, Any]:
        namespace = str(dep.get("namespace", ""))
        pods = dep.get("pods") or []
        if isinstance(pods, tuple):
            pods = list(pods)
        async def _cached_logs() -> dict[str, Any]:
            return {
                "source": "cached",
                "lines": [],
                "flagged": [],
                "bulletins": [],
                "scanned_pod": None,
            }

        log_coro = (
            _logs_for_deployment(cluster_id, namespace, pods, kc)
            if refresh_logs
            else _cached_logs()
        )
        metrics, logs, pod_health = await asyncio.gather(
            _metrics_for_deployment(cluster_id, namespace),
            log_coro,
            _pod_readiness(kc, namespace, pods),
        )
        status, issues = _assess_deployment(
            has_prometheus=bool(dep.get("has_prometheus")),
            local_port=dep.get("local_port"),
            metrics=metrics,
            logs=logs,
            pod_health=pod_health,
        )
        mem_pct = metrics.get("memory_usage_pct")
        if mem_pct is not None:
            mem_pct = round(mem_pct, 2)
        display_metrics: dict[str, float | None] = {
            "deployed_flows": metrics.get("deployed_flows"),
            "memory_usage_pct": mem_pct,
        }
        return {
            "name": namespace,
            "namespace": namespace,
            "status": status,
            "issues": issues,
            "pods_ready": pod_health.get("ready"),
            "pods_total": pod_health.get("total"),
            "has_prometheus": dep.get("has_prometheus"),
            "local_port": dep.get("local_port"),
            "pods": pods,
            "metrics": display_metrics,
            "logs": logs,
        }

    deployment_rows = list(await asyncio.gather(*[build_row(d) for d in raw_deps]))

    count_promql = apply_cluster_label(
        'sum(count by (nifi_namespace) (nifi_amount_threads_active{cluster="$cluster", component_type="RootProcessGroup"}))',
        cluster_id,
    )
    deployment_count_metric = await _prom_scalar(count_promql)

    return {
        "cluster_id": cluster_id,
        "display_name": cluster.display_name,
        "deployment_count": len(deployment_rows),
        "deployment_count_metric": deployment_count_metric,
        "deployments": deployment_rows,
        "refetch_hint_sec": 2,
    }

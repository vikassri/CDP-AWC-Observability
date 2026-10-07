from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Any

from backend.app.schemas import LogSearchIn
from backend.app.services.logs_search import search_logs
from backend.app.services.prometheus_client import query_prometheus
from backend.app.services.promql_helpers import apply_cluster_label

_ERROR_LINE = re.compile(r"(?i)(error|exception|failed|fatal)")


async def prom_scalar(promql: str) -> float | None:
    try:
        payload = await query_prometheus(promql)
    except Exception:  # noqa: BLE001
        return None
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


async def prom_scalar_cluster(query_template: str, cluster_id: str, **replacements: str) -> float | None:
    promql = query_template
    for key, val in replacements.items():
        promql = promql.replace(f"${key}", val)
    return await prom_scalar(apply_cluster_label(promql, cluster_id))


async def kubectl_log_tail(kubeconfig: Path, namespace: str, pod: str, *, tail: int = 35) -> list[str]:
    if not pod:
        return []
    proc = await asyncio.create_subprocess_exec(
        "kubectl",
        f"--kubeconfig={kubeconfig}",
        "logs",
        pod,
        "-n",
        namespace,
        f"--tail={tail}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _stderr = await asyncio.wait_for(proc.communicate(), timeout=45)
    if proc.returncode != 0:
        return []
    return (stdout.decode(errors="replace")).splitlines()


async def logs_for_workload(
    *,
    cluster_id: str,
    product: str,
    namespace: str,
    kubeconfig: Path,
    pod: str,
) -> dict[str, Any]:
    os_hits = await search_logs(
        LogSearchIn(cluster=cluster_id, product=product, namespace=namespace, q="*", size=20)
    )
    raw_hits = os_hits.get("hits")
    hit_list = raw_hits.get("hits") if isinstance(raw_hits, dict) else raw_hits if isinstance(raw_hits, list) else []
    os_lines: list[str] = []
    for hit in hit_list or []:
        src = hit.get("_source") or {}
        body = src.get("body") or src.get("message") or ""
        if body:
            os_lines.append(str(body).strip())

    kubectl_lines = await kubectl_log_tail(kubeconfig, namespace, pod) if pod else []
    combined = os_lines if os_lines else kubectl_lines
    flagged = [line for line in combined if _ERROR_LINE.search(line)]
    return {
        "source": "opensearch" if os_lines else ("kubectl" if kubectl_lines else "none"),
        "lines": combined[:25],
        "flagged": flagged[:12],
        "scanned_pod": pod or None,
    }


def finalize_status(issues: list[str]) -> tuple[str, list[str]]:
    if any("critical" in i.lower() or "failed" in i.lower() for i in issues[:2]):
        return "critical", issues
    if issues:
        return "degraded", issues
    return "healthy", issues

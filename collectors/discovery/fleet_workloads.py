"""Discover NiFi / Trino / Spark / Flink / Airflow workloads via registered kubeconfigs."""
from __future__ import annotations

import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

_LEGACY = Path(__file__).resolve().parents[1] / "legacy"
if str(_LEGACY) not in sys.path:
    sys.path.insert(0, str(_LEGACY))

from collectors.common.registry import RegisteredCluster, load_registered_clusters  # noqa: E402

_PRODUCT_DISCOVERERS: dict[str, str] = {
    "nifi": "nifi",
    "trino": "trino",
    "spark": "spark",
    "flink": "flink",
    "airflow": "airflow",
}


def _serialize(obj: Any) -> Any:
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, tuple):
        return list(obj)
    return obj


def _discover_nifi(cluster: RegisteredCluster) -> dict[str, Any]:
    from nifi_discovery import discover_in_cluster  # type: ignore[import-not-found]

    deps = discover_in_cluster(cluster.id, cluster.kubeconfig)
    return {
        "deployments": [_serialize(d) for d in deps],
        "metrics": "federate dfx-nifi-web + nifi_status_exporter",
        "logs": "nifi pod logs → OTel when nifi_logs collector enabled",
    }


def _discover_trino(cluster: RegisteredCluster) -> dict[str, Any]:
    from trino_discovery import discover_in_cluster  # type: ignore[import-not-found]

    targets = discover_in_cluster(cluster.id, cluster.kubeconfig)
    return {
        "engines": [_serialize(t) for t in targets],
        "metrics": "trino_status_exporter (/v1/status)",
        "logs": "coordinator/worker logs → OTel",
    }


def _discover_spark(cluster: RegisteredCluster) -> dict[str, Any]:
    from spark_discovery import discover_applications, discover_log_pods  # type: ignore[import-not-found]

    apps = discover_applications(cluster.id, cluster.kubeconfig)
    pods = discover_log_pods(cluster.id, cluster.kubeconfig)
    return {
        "applications": [_serialize(a) for a in apps],
        "log_pods": [_serialize(p) for p in pods],
        "metrics": "spark_status_exporter (SparkApplication CR state)",
        "logs": "operator/driver/executor logs → OTel",
    }


def _discover_flink(cluster: RegisteredCluster) -> dict[str, Any]:
    from flink_discovery import (  # type: ignore[import-not-found]
        discover_deployments,
        discover_log_pods,
        discover_session_jobs,
    )

    deps = discover_deployments(cluster.id, cluster.kubeconfig)
    jobs = discover_session_jobs(cluster.id, cluster.kubeconfig)
    pods = discover_log_pods(cluster.id, cluster.kubeconfig)
    return {
        "deployments": [_serialize(d) for d in deps],
        "session_jobs": [_serialize(j) for j in jobs],
        "log_pods": [_serialize(p) for p in pods],
        "metrics": "flink_status_exporter",
        "logs": "JM/taskmanager logs → OTel",
    }


def _discover_airflow(cluster: RegisteredCluster) -> dict[str, Any]:
    from airflow_discovery import discover_in_cluster  # type: ignore[import-not-found]

    targets = discover_in_cluster(cluster.id, cluster.kubeconfig)
    return {
        "pods": [_serialize(t) for t in targets],
        "metrics": "airflow_status_exporter",
        "logs": "scheduler/webserver/worker logs → OTel",
    }


def discover_for_cluster(cluster_id: str) -> dict[str, Any]:
    entry = next((c for c in load_registered_clusters() if c.id == cluster_id), None)
    if not entry:
        return {"cluster_id": cluster_id, "error": "unknown cluster", "workloads": {}}
    if not entry.kubeconfig.is_file():
        return {
            "cluster_id": cluster_id,
            "product": entry.product,
            "error": f"kubeconfig missing: {entry.kubeconfig}",
            "workloads": {},
        }

    product = entry.product
    if product not in _PRODUCT_DISCOVERERS:
        return {
            "cluster_id": cluster_id,
            "product": product,
            "context": entry.context,
            "kubeconfig": str(entry.kubeconfig),
            "workloads": {},
            "note": f"No application discovery rules for product '{product}' yet",
        }

    discover_fn = {
        "nifi": _discover_nifi,
        "trino": _discover_trino,
        "spark": _discover_spark,
        "flink": _discover_flink,
        "airflow": _discover_airflow,
    }[product]

    try:
        workloads = discover_fn(entry)
    except Exception as exc:  # noqa: BLE001
        return {
            "cluster_id": cluster_id,
            "product": product,
            "context": entry.context,
            "kubeconfig": str(entry.kubeconfig),
            "error": str(exc),
            "workloads": {},
        }

    return {
        "cluster_id": cluster_id,
        "product": product,
        "context": entry.context,
        "kubeconfig": str(entry.kubeconfig),
        "workloads": workloads,
    }


def discover_fleet() -> list[dict[str, Any]]:
    return [discover_for_cluster(c.id) for c in load_registered_clusters()]

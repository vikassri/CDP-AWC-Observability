#!/usr/bin/env python3
"""Discover CDF NiFi deployments across hub kubeconfig files."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


NS_LABEL_SELECTOR = "app.kubernetes.io/name=nifi,app.kubernetes.io/instance=cloudera-data-flow"
POD_LABEL_SELECTOR = "app.kubernetes.io/part-of=nifi,app.kubernetes.io/component=nifi"
PROMETHEUS_SVC = "prometheus"
PROMETHEUS_PORT = 19090
DEFAULT_KCFG_DIR = Path("/etc/prometheus/kubeconfig")
BASE_LOCAL_PORT = 19090


@dataclass(frozen=True)
class NiFiDeployment:
    cluster: str
    kubeconfig: str
    namespace: str
    display_name: str
    has_prometheus: bool
    pods: tuple[str, ...]
    local_port: int | None = None

    def to_json(self) -> dict:
        return asdict(self)


def _kubectl(kubeconfig: Path, *args: str, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["kubectl", f"--kubeconfig={kubeconfig}", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def list_kubeconfigs(kcfg_dir: Path) -> list[tuple[str, Path]]:
    from collectors.common.registry import list_kubeconfigs_for_product

    registered = list_kubeconfigs_for_product(kcfg_dir, "nifi")
    if registered:
        return registered
    if not kcfg_dir.is_dir():
        return []
    return [(path.stem, path) for path in sorted(kcfg_dir.glob("*.yaml"))]


def discover_in_cluster(cluster: str, kubeconfig: Path) -> list[NiFiDeployment]:
    proc = _kubectl(
        kubeconfig,
        "get",
        "ns",
        "-l",
        NS_LABEL_SELECTOR,
        "-o",
        "json",
    )
    if proc.returncode != 0:
        return []

    try:
        ns_items = json.loads(proc.stdout).get("items", [])
    except json.JSONDecodeError:
        return []

    deployments: list[NiFiDeployment] = []
    for item in ns_items:
        meta = item["metadata"]
        namespace = meta["name"]
        labels = meta.get("labels") or {}
        annotations = meta.get("annotations") or {}
        # Primary label is the NiFi namespace (e.g. dfx-daily-account-table-ingest-ns).
        display_name = namespace
        prom = _kubectl(kubeconfig, "get", "svc", PROMETHEUS_SVC, "-n", namespace)
        has_prometheus = prom.returncode == 0

        pod_proc = _kubectl(
            kubeconfig,
            "get",
            "pods",
            "-n",
            namespace,
            "-l",
            POD_LABEL_SELECTOR,
            "-o",
            "jsonpath={.items[*].metadata.name}",
        )
        pods = tuple(p for p in (pod_proc.stdout or "").split() if p)

        deployments.append(
            NiFiDeployment(
                cluster=cluster,
                kubeconfig=str(kubeconfig),
                namespace=namespace,
                display_name=str(display_name),
                has_prometheus=has_prometheus,
                pods=pods,
            )
        )
    return deployments


def assign_ports(deployments: list[NiFiDeployment]) -> list[NiFiDeployment]:
    """Stable local port per metrics-ready deployment."""
    metrics_ready = sorted(
        [d for d in deployments if d.has_prometheus],
        key=lambda d: (d.cluster, d.namespace),
    )
    port_by_key: dict[tuple[str, str], int] = {}
    for idx, dep in enumerate(metrics_ready):
        port_by_key[(dep.cluster, dep.namespace)] = BASE_LOCAL_PORT + idx

    result: list[NiFiDeployment] = []
    for dep in deployments:
        port = port_by_key.get((dep.cluster, dep.namespace))
        result.append(
            NiFiDeployment(
                cluster=dep.cluster,
                kubeconfig=dep.kubeconfig,
                namespace=dep.namespace,
                display_name=dep.display_name,
                has_prometheus=dep.has_prometheus,
                pods=dep.pods,
                local_port=port,
            )
        )
    return result


def discover_all(
    kcfg_dir: Path = DEFAULT_KCFG_DIR,
    *,
    metrics_only: bool = True,
) -> list[NiFiDeployment]:
    all_deps: list[NiFiDeployment] = []
    for cluster, kc_path in list_kubeconfigs(kcfg_dir):
        found = discover_in_cluster(cluster, kc_path)
        if metrics_only:
            found = [d for d in found if d.has_prometheus]
        all_deps.extend(found)
    return assign_ports(all_deps)


def prometheus_file_sd(deployments: list[NiFiDeployment]) -> list[dict]:
    scrape_host = os.environ.get("CPW_SCRAPE_HOST", "127.0.0.1")
    groups: list[dict] = []
    for dep in deployments:
        if not dep.has_prometheus or dep.local_port is None:
            continue
        groups.append(
            {
                "targets": [f"{scrape_host}:{dep.local_port}"],
                "labels": {
                    "cluster": dep.cluster,
                    "nifi_namespace": dep.namespace,
                },
            }
        )
    return groups


def main() -> None:
    kcfg_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_KCFG_DIR
    deps = discover_all(kcfg_dir)
    print(json.dumps([d.to_json() for d in deps], indent=2))


if __name__ == "__main__":
    main()

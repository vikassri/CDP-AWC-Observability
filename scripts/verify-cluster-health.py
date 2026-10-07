#!/usr/bin/env python3
"""Verify Kubernetes API reachability for all clusters in config/clusters.yaml."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from backend.app.config_loader import load_clusters, resolve_kubeconfig  # noqa: E402
from backend.app.services.k8s_pool import check_cluster_health  # noqa: E402


async def main() -> int:
    failed = 0
    for cluster in load_clusters():
        kc = resolve_kubeconfig(cluster)
        result = await check_cluster_health(kc, cluster.context)
        ok = "OK" if result.get("healthy") else "FAIL"
        print(f"[{ok}] {cluster.id:8} {cluster.context:16} {result.get('message', '')}")
        if not result.get("healthy"):
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

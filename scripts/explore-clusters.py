#!/usr/bin/env python3
"""Run kubectl discovery for every cluster in config/clusters.yaml."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
os.environ.setdefault("CPW_CONFIG_DIR", str(REPO / "config"))
os.environ.setdefault("CPW_KUBECONFIG_DIR", str(REPO / "kubeconfigs"))

from collectors.discovery.fleet_workloads import discover_fleet, discover_for_cluster  # noqa: E402


def main() -> int:
    cluster_id = sys.argv[1] if len(sys.argv) > 1 else ""
    if cluster_id:
        payload = discover_for_cluster(cluster_id)
    else:
        payload = {"clusters": discover_fleet()}
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

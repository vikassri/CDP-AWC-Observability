from __future__ import annotations

import os
from pathlib import Path

from collectors.common.registry import load_registered_clusters


def test_load_registered_clusters_has_five_products() -> None:
    repo = Path(__file__).resolve().parents[2]
    os.environ["CPW_CONFIG_DIR"] = str(repo / "config")
    os.environ["CPW_KUBECONFIG_DIR"] = str(repo / "kubeconfigs")
    clusters = load_registered_clusters()
    assert len(clusters) >= 5
    products = {c.product for c in clusters}
    assert "nifi" in products
    assert "trino" in products

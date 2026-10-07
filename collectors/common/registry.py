"""Map clusters.yaml entries to kubeconfig paths for discovery collectors."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from collectors.common.paths import repo_path


@dataclass(frozen=True)
class RegisteredCluster:
    id: str
    product: str
    context: str
    kubeconfig: Path


def _config_dir() -> Path:
    raw = os.environ.get("CPW_CONFIG_DIR", "")
    if raw:
        path = Path(raw)
        return path if path.is_absolute() else repo_path(raw)
    return repo_path("config")


def _kubeconfig_dir() -> Path:
    raw = os.environ.get("CPW_KUBECONFIG_DIR", "")
    if raw:
        path = Path(raw)
        return path if path.is_absolute() else repo_path(raw)
    return repo_path("kubeconfigs")


def load_registered_clusters() -> list[RegisteredCluster]:
    path = _config_dir() / "clusters.yaml"
    if not path.is_file():
        return []
    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    kcfg_root = _kubeconfig_dir()
    out: list[RegisteredCluster] = []
    for item in raw.get("clusters") or []:
        cluster_id = str(item.get("id", "")).strip()
        if not cluster_id:
            continue
        rel = str(item.get("kubeconfig", "")).strip()
        kc = Path(rel)
        if not kc.is_absolute():
            kc = repo_path(rel) if rel.startswith("kubeconfigs") else kcfg_root / f"{cluster_id}.yaml"
        if not kc.is_file() and rel:
            kc = repo_path(rel)
        out.append(
            RegisteredCluster(
                id=cluster_id,
                product=str(item.get("product", "")).lower(),
                context=str(item.get("context", "")),
                kubeconfig=kc,
            )
        )
    return out


def list_kubeconfigs_for_product(
    kcfg_dir: Path,
    product: str | None = None,
) -> list[tuple[str, Path]]:
    """Prefer clusters.yaml registry; fall back to globbing kcfg_dir."""
    registered = load_registered_clusters()
    if registered:
        pairs: list[tuple[str, Path]] = []
        for entry in registered:
            if product and entry.product != product:
                continue
            if entry.kubeconfig.is_file():
                pairs.append((entry.id, entry.kubeconfig))
        if pairs:
            return pairs
    if not kcfg_dir.is_dir():
        return []
    return [(p.stem, p) for p in sorted(kcfg_dir.glob("*.yaml"))]

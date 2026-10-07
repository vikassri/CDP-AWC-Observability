from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from backend.app.settings import settings


class ClusterConfig(BaseModel):
    id: str
    display_name: str
    product: str
    context: str
    kubeconfig: str
    awc_engine_id: str = ""
    collectors: list[str] = Field(default_factory=list)
    knox_metrics_url: str = ""


class AwcConfig(BaseModel):
    console_base_url: str
    engines_path: str


def load_clusters() -> list[ClusterConfig]:
    path = settings.cpw_config_dir / "clusters.yaml"
    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return [ClusterConfig.model_validate(item) for item in raw.get("clusters") or []]


def load_awc() -> AwcConfig:
    path = settings.cpw_config_dir / "awc.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return AwcConfig.model_validate(raw)


def resolve_kubeconfig(cluster: ClusterConfig) -> Path:
    path = Path(cluster.kubeconfig)
    if not path.is_absolute():
        path = settings.cpw_config_dir.parent / path
    return path

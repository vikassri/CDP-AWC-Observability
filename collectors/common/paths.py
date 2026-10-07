from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def repo_path(*parts: str) -> Path:
    return REPO_ROOT.joinpath(*parts)


def kubeconfig_dir() -> Path:
    return Path(os.environ.get("CPW_KUBECONFIG_DIR", repo_path("kubeconfigs")))


def file_sd_dir() -> Path:
    return Path(os.environ.get("CPW_FILE_SD_DIR", repo_path("deploy/data/prometheus/file_sd")))


def log_script() -> Path:
    return repo_path("collectors/logging/kubectl_logs_to_otel.py")


def state_dir(name: str) -> Path:
    base = Path(os.environ.get("CPW_STATE_DIR", repo_path("deploy/data/state")))
    path = base / name
    path.mkdir(parents=True, exist_ok=True)
    return path

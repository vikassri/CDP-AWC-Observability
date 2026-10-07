from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

from backend.app.config_loader import load_clusters
from backend.app.settings import REPO_ROOT, settings

log = logging.getLogger(__name__)

LEGACY = REPO_ROOT / "collectors" / "legacy"

EXPORTER_SCRIPTS: dict[str, tuple[str, str]] = {
    "nifi": ("nifi_status_exporter.py", "NIFI_KUBECONFIG"),
    "trino": ("trino_status_exporter.py", "TRINO_KUBECONFIG_DIR"),
    "spark": ("spark_status_exporter.py", "SPARK_KUBECONFIG_DIR"),
    "flink": ("flink_status_exporter.py", "FLINK_KUBECONFIG_DIR"),
    "airflow": ("airflow_status_exporter.py", "AIRFLOW_KUBECONFIG_DIR"),
}

KCFG_ENV_KEYS = [
    "TRINO_KUBECONFIG_DIR",
    "SPARK_KUBECONFIG_DIR",
    "FLINK_KUBECONFIG_DIR",
    "AIRFLOW_KUBECONFIG_DIR",
]

_procs: dict[str, subprocess.Popen[bytes]] = {}


def _products_enabled() -> set[str]:
    products: set[str] = set()
    for cluster in load_clusters():
        products.add(cluster.product)
    return products


def _is_alive(proc: subprocess.Popen[bytes] | None) -> bool:
    return proc is not None and proc.poll() is None


def start_status_exporters() -> list[str]:
    started: list[str] = []
    kcfg_dir = str(settings.cpw_kubeconfig_dir)
    products = _products_enabled()

    for product, (script, env_key) in EXPORTER_SCRIPTS.items():
        if product not in products and product != "nifi":
            continue
        if product == "nifi" and "nifi" not in {
            c.product for c in load_clusters()
        }:
            continue

        if _is_alive(_procs.get(product)):
            continue

        script_path = LEGACY / script
        if not script_path.is_file():
            log.warning("Missing status exporter script %s", script_path)
            continue

        env = os.environ.copy()
        for key in KCFG_ENV_KEYS:
            env[key] = kcfg_dir
        if product == "nifi":
            nifi_kc = settings.cpw_kubeconfig_dir / "cdf.yaml"
            env["NIFI_KUBECONFIG"] = str(nifi_kc)
            env["NIFI_KUBECONFIG_DIR"] = kcfg_dir
        else:
            env[env_key] = kcfg_dir

        proc = subprocess.Popen(
            [sys.executable, str(script_path)],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            cwd=str(REPO_ROOT),
        )
        _procs[product] = proc
        started.append(product)
        log.info("Started %s status exporter pid=%s", product, proc.pid)

    return started


def stop_status_exporters() -> None:
    for product, proc in list(_procs.items()):
        if _is_alive(proc):
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
        _procs.pop(product, None)


def status_exporters_state() -> list[dict]:
    rows: list[dict] = []
    for product, proc in _procs.items():
        alive = _is_alive(proc)
        err = ""
        if proc.stderr and proc.poll() is not None:
            err = (proc.stderr.read() or b"")[:200].decode(errors="replace")
        rows.append({"product": product, "running": alive, "pid": proc.pid if alive else None, "error": err})
    return rows

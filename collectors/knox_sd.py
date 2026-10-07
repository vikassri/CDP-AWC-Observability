"""Optional Knox HTTPS scrape targets written to file_sd when knox_metrics_url is set."""
from __future__ import annotations

from urllib.parse import urlparse

import yaml

from collectors.common.paths import file_sd_dir, repo_path
from collectors.common.prometheus_sd import write_file_sd


def _parse_knox_url(url: str) -> tuple[str, str]:
    """Return (host:port target, metrics_path) for Prometheus file_sd."""
    if "://" not in url:
        url = f"https://{url}"
    parsed = urlparse(url)
    host = parsed.hostname or ""
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    target = f"{host}:{port}"
    path = parsed.path or "/metrics/prometheus"
    if not path.startswith("/"):
        path = f"/{path}"
    return target, path


def sync_knox_targets() -> list[dict]:
    clusters_path = repo_path("config/clusters.yaml")
    if not clusters_path.is_file():
        write_file_sd(file_sd_dir() / "nifi_knox.json", [])
        return []
    raw = yaml.safe_load(clusters_path.read_text(encoding="utf-8")) or {}
    groups: list[dict] = []
    for cluster in raw.get("clusters") or []:
        url = (cluster.get("knox_metrics_url") or "").strip()
        if not url:
            continue
        target, metrics_path = _parse_knox_url(url)
        groups.append(
            {
                "targets": [target],
                "labels": {
                    "cluster": cluster.get("id", ""),
                    "product": cluster.get("product", ""),
                    "__metrics_path__": metrics_path,
                },
            }
        )
    write_file_sd(file_sd_dir() / "nifi_knox.json", groups)
    return groups

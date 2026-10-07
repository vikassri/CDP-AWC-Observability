from __future__ import annotations

from datetime import datetime, timezone

from backend.app.config_loader import AwcConfig, ClusterConfig, load_awc, load_clusters


def fleet_console_url(awc: AwcConfig | None = None) -> str:
    cfg = awc or load_awc()
    return f"{cfg.console_base_url.rstrip('/')}{cfg.engines_path}"


def engine_console_url(cluster: ClusterConfig, awc: AwcConfig | None = None) -> str:
    cfg = awc or load_awc()
    base = cfg.console_base_url.rstrip("/")
    path = cfg.engines_path
    if not cluster.awc_engine_id:
        return f"{base}{path}"
    joiner = "&" if "?" in path else "?"
    return f"{base}{path}{joiner}engine={cluster.awc_engine_id}"


def build_engine_catalog() -> dict:
    awc = load_awc()
    clusters = load_clusters()
    engines = [
        {
            "id": c.awc_engine_id or c.id,
            "cluster_id": c.id,
            "display_name": c.display_name,
            "product": c.product,
            "context": c.context,
            "collectors": c.collectors,
            "awc_console_url": engine_console_url(c, awc),
            "knox_metrics_configured": bool((c.knox_metrics_url or "").strip()),
        }
        for c in clusters
    ]
    return {
        "source": "static_clusters_yaml",
        "fleet_console_url": fleet_console_url(awc),
        "console_base_url": awc.console_base_url,
        "engines_path": awc.engines_path,
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "engines": engines,
    }

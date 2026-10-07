from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from backend.app.config_loader import load_clusters
from backend.app.settings import REPO_ROOT, settings

log = logging.getLogger(__name__)

_REPO = str(REPO_ROOT)
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

COLLECTOR_MAP: dict[str, str] = {
    "nifi_metrics": "collectors.hub_agents.nifi.NiFiHubAgent",
    "trino_metrics": "collectors.hub_agents.trino.TrinoHubAgent",
    "spark_metrics": "collectors.hub_agents.spark.SparkHubAgent",
    "flink_metrics": "collectors.hub_agents.flink.FlinkHubAgent",
    "airflow_metrics": "collectors.hub_agents.airflow.AirflowHubAgent",
}


def _import_agent(class_path: str):
    module_name, class_name = class_path.rsplit(".", 1)
    mod = __import__(module_name, fromlist=[class_name])
    return getattr(mod, class_name)()


class CollectorSupervisor:
    def __init__(self) -> None:
        self._heartbeats: dict[str, dict] = {}
        self._task: asyncio.Task | None = None
        self._agents: list = []

    def _env_setup(self) -> None:
        os.environ.setdefault("CPW_CONFIG_DIR", str(settings.cpw_config_dir))
        os.environ.setdefault("CPW_KUBECONFIG_DIR", str(settings.cpw_kubeconfig_dir))
        os.environ.setdefault("CPW_FILE_SD_DIR", str(settings.cpw_file_sd_dir))
        os.environ.setdefault("CPW_OTEL_LOGS_ENDPOINT", settings.cpw_otel_logs_endpoint)
        os.environ.setdefault("CPW_SCRAPE_HOST", settings.cpw_scrape_host)

    def _build_agents(self) -> None:
        self._agents.clear()
        enabled: set[str] = set()
        for cluster in load_clusters():
            enabled.update(cluster.collectors)
        for collector_name in enabled:
            if collector_name.endswith("_logs"):
                continue
            class_path = COLLECTOR_MAP.get(collector_name)
            if not class_path:
                continue
            self._agents.append(_import_agent(class_path))

    async def start(self) -> None:
        self._env_setup()
        self._build_agents()
        from backend.app.services.status_exporters import start_status_exporters

        await asyncio.to_thread(start_status_exporters)
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        from backend.app.services.status_exporters import stop_status_exporters

        await asyncio.to_thread(stop_status_exporters)

    async def _loop(self) -> None:
        from collectors.knox_sd import sync_knox_targets

        while True:
            try:
                sync_knox_targets()
            except Exception:  # noqa: BLE001
                log.exception("knox file_sd sync failed")
            for agent in self._agents:
                hb = await asyncio.to_thread(agent.run_once)
                self._heartbeats[agent.name] = {
                    "name": hb.name,
                    "last_ok_at": hb.last_ok_at.isoformat() if hb.last_ok_at else None,
                    "last_error": hb.last_error,
                    "detail": hb.detail,
                }
            await asyncio.sleep(settings.collector_interval_sec)

    def status(self) -> list[dict]:
        return list(self._heartbeats.values())


supervisor = CollectorSupervisor()

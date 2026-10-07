from __future__ import annotations

import os
import sys
from pathlib import Path

from collectors.common.paths import file_sd_dir, kubeconfig_dir, log_script
from collectors.hub_agents.base import CollectorHeartbeat, HubAgent

_LEGACY = Path(__file__).resolve().parents[1] / "legacy"
if str(_LEGACY) not in sys.path:
    sys.path.insert(0, str(_LEGACY))


class AirflowHubAgent(HubAgent):
    name = "airflow_metrics"

    def __init__(self) -> None:
        import airflow_hub_agent as legacy  # type: ignore[import-not-found]
        import airflow_prometheus_sd as sd  # type: ignore[import-not-found]

        self._legacy = legacy
        sd.OUT = file_sd_dir() / "airflow_status.json"
        legacy.KCFG_DIR = kubeconfig_dir()
        legacy.LOG_SCRIPT = log_script()
        legacy.OTEL_LOGS_ENDPOINT = os.environ.get(
            "CPW_OTEL_LOGS_ENDPOINT", "http://127.0.0.1:4318/v1/logs"
        )

    def tick(self) -> CollectorHeartbeat:
        from airflow_discovery import discover_all  # type: ignore[import-not-found]

        targets = discover_all(kubeconfig_dir())
        self._legacy.sync(targets)
        log_streams = len(getattr(self._legacy, "_log_streams", {}))
        return CollectorHeartbeat(
            name=self.name,
            detail={"pods": len(targets), "log_streams": log_streams},
        )

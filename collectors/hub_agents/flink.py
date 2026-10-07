from __future__ import annotations

import os
import sys
from pathlib import Path

from collectors.common.paths import file_sd_dir, kubeconfig_dir, log_script
from collectors.hub_agents.base import CollectorHeartbeat, HubAgent

_LEGACY = Path(__file__).resolve().parents[1] / "legacy"
if str(_LEGACY) not in sys.path:
    sys.path.insert(0, str(_LEGACY))


class FlinkHubAgent(HubAgent):
    name = "flink_metrics"

    def __init__(self) -> None:
        import flink_hub_agent as legacy  # type: ignore[import-not-found]
        import flink_prometheus_sd as sd  # type: ignore[import-not-found]

        self._legacy = legacy
        sd.OUT = file_sd_dir() / "flink_status.json"
        legacy.KCFG_DIR = kubeconfig_dir()
        legacy.LOG_SCRIPT = log_script()
        legacy.OTEL_LOGS_ENDPOINT = os.environ.get(
            "CPW_OTEL_LOGS_ENDPOINT", "http://127.0.0.1:4318/v1/logs"
        )

    def tick(self) -> CollectorHeartbeat:
        from flink_discovery import discover_all  # type: ignore[import-not-found]

        pods, deps, jobs = discover_all(kubeconfig_dir())
        self._legacy.sync(pods)
        log_streams = len(getattr(self._legacy, "_log_streams", {}))
        return CollectorHeartbeat(
            name=self.name,
            detail={
                "deployments": len(deps),
                "session_jobs": len(jobs),
                "log_pods": len(pods),
                "log_streams": log_streams,
            },
        )

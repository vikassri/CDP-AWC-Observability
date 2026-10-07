from __future__ import annotations

import os
import sys
from pathlib import Path

from collectors.common.paths import file_sd_dir, kubeconfig_dir, log_script, state_dir
from collectors.hub_agents.base import CollectorHeartbeat, HubAgent

_LEGACY = Path(__file__).resolve().parents[1] / "legacy"
if str(_LEGACY) not in sys.path:
    sys.path.insert(0, str(_LEGACY))


class NiFiHubAgent(HubAgent):
    name = "nifi_metrics"

    def __init__(self) -> None:
        import nifi_hub_agent as legacy  # type: ignore[import-not-found]

        self._legacy = legacy
        legacy.PROMETHEUS_FILE_SD = file_sd_dir() / "nifi_federate.json"
        legacy.STATE_DIR = state_dir("nifi-hub")
        legacy.KCFG_DIR = kubeconfig_dir()
        legacy.LOG_SCRIPT = log_script()
        legacy.LOG_FORWARDER_DIR = log_script().parent
        legacy.OTEL_LOGS_ENDPOINT = os.environ.get(
            "CPW_OTEL_LOGS_ENDPOINT", "http://127.0.0.1:4318/v1/logs"
        )

    def tick(self) -> CollectorHeartbeat:
        from nifi_discovery import discover_all  # type: ignore[import-not-found]

        deps = discover_all(kubeconfig_dir())
        self._legacy.sync(deps)
        metrics_ready = sum(1 for d in deps if d.has_prometheus and d.local_port)
        log_streams = len(getattr(self._legacy, "_log_streams", {}))
        return CollectorHeartbeat(
            name=self.name,
            detail={
                "deployments": len(deps),
                "federate_targets": metrics_ready,
                "log_streams": log_streams,
            },
        )

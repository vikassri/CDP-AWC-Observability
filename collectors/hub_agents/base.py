from __future__ import annotations

import abc
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger(__name__)


@dataclass
class CollectorHeartbeat:
    name: str
    last_ok_at: datetime | None = None
    last_error: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)


class HubAgent(abc.ABC):
    """One product collector loop (discovery, file_sd, optional log streams)."""

    name: str

    @abc.abstractmethod
    def tick(self) -> CollectorHeartbeat:
        """Single discovery / refresh cycle."""

    def run_once(self) -> CollectorHeartbeat:
        try:
            hb = self.tick()
            hb.last_ok_at = datetime.now(timezone.utc)
            return hb
        except Exception as exc:  # noqa: BLE001 — surface to supervisor
            log.exception("%s tick failed", self.name)
            return CollectorHeartbeat(name=self.name, last_error=str(exc))

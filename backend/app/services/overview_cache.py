from __future__ import annotations

import time
from typing import Any

_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_tick = 0


def bump_overview_tick() -> int:
    global _tick
    _tick += 1
    return _tick


def refresh_logs_this_cycle() -> bool:
    """Refresh log tails every 3rd overview build to cut kubectl load."""
    return bump_overview_tick() % 3 == 0


def get_cached(key: str, ttl_sec: float) -> dict[str, Any] | None:
    entry = _cache.get(key)
    if not entry:
        return None
    ts, payload = entry
    if time.time() - ts > ttl_sec:
        return None
    out = dict(payload)
    out["cached"] = True
    return out


def set_cached(key: str, payload: dict[str, Any]) -> None:
    _cache[key] = (time.time(), payload)


def _deployment_key(row: dict[str, Any]) -> tuple[str, str]:
    return (str(row.get("namespace") or ""), str(row.get("name") or ""))


def _logs_need_merge(logs: dict[str, Any]) -> bool:
    if not logs:
        return True
    if logs.get("lines") or logs.get("flagged") or logs.get("bulletins"):
        return False
    source = str(logs.get("source") or "")
    return source in ("cached", "skipped", "pending", "none")


def merge_logs_from_previous(cache_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    """When log tails are skipped, reuse logs from the last cached overview."""
    entry = _cache.get(cache_key)
    if not entry:
        return payload
    prev_rows = (entry[1].get("deployments") or []) if isinstance(entry[1], dict) else []
    prev_logs = {_deployment_key(r): r.get("logs") for r in prev_rows if isinstance(r, dict)}
    if not prev_logs:
        return payload
    out = dict(payload)
    merged: list[dict[str, Any]] = []
    for row in out.get("deployments") or []:
        if not isinstance(row, dict):
            merged.append(row)
            continue
        logs = row.get("logs") or {}
        if _logs_need_merge(logs):
            prior = prev_logs.get(_deployment_key(row))
            if prior and not _logs_need_merge(prior):
                row = {**row, "logs": prior}
        merged.append(row)
    out["deployments"] = merged
    return out

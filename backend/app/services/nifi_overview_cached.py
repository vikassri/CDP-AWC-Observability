from __future__ import annotations

from typing import Any

from backend.app.settings import settings
from backend.app.services.nifi_overview import nifi_overview
from backend.app.services.overview_cache import (
    get_cached,
    merge_logs_from_previous,
    refresh_logs_this_cycle,
    set_cached,
)


async def nifi_overview_cached(cluster_id: str) -> dict[str, Any]:
    cache_key = f"nifi:{cluster_id}"
    cached = get_cached(cache_key, settings.cpw_overview_cache_sec)
    if cached:
        return cached

    refresh_logs = refresh_logs_this_cycle()
    raw = await nifi_overview(cluster_id, refresh_logs=refresh_logs)
    result = dict(raw)
    if not refresh_logs:
        result = merge_logs_from_previous(cache_key, result)
    set_cached(cache_key, result)
    return result

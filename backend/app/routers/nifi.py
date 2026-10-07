from __future__ import annotations

from fastapi import APIRouter, Query

from backend.app.services.nifi_overview_cached import nifi_overview_cached

router = APIRouter(prefix="/nifi", tags=["nifi"])


@router.get("/overview")
async def get_nifi_overview(cluster: str = Query(default="cdf", min_length=1)) -> dict:
    return await nifi_overview_cached(cluster)

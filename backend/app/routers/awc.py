from __future__ import annotations

from fastapi import APIRouter

from backend.app.services.awc_catalog import build_engine_catalog, fleet_console_url

router = APIRouter(prefix="/awc", tags=["awc"])


@router.get("/catalog")
async def awc_catalog() -> dict:
    return build_engine_catalog()


@router.get("/console")
async def awc_console_links() -> dict[str, str]:
    return {"fleet_url": fleet_console_url()}

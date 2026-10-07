from __future__ import annotations

from fastapi import APIRouter

from backend.app.services.collector_supervisor import supervisor

router = APIRouter(prefix="/collectors", tags=["collectors"])


@router.get("")
@router.get("/")
@router.get("/status")
async def collectors_status() -> list[dict]:
    return supervisor.status()

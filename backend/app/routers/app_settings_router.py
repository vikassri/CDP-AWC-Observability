from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from fastapi import APIRouter

from backend.app.services.app_settings import (
    apply_settings_patch,
    build_settings_snapshot,
    probe_inference,
)

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsPatchBody(BaseModel):
    inference: dict[str, Any] | None = None
    cloudera: dict[str, Any] | None = None
    telemetry: dict[str, Any] | None = None
    alerts: dict[str, Any] | None = None


@router.get("")
async def get_app_settings() -> dict[str, Any]:
    return build_settings_snapshot()


@router.patch("")
async def patch_app_settings(body: SettingsPatchBody) -> dict[str, Any]:
    return apply_settings_patch(body.model_dump(exclude_none=True))


@router.post("/test-inference")
async def test_inference() -> dict[str, Any]:
    return await probe_inference()

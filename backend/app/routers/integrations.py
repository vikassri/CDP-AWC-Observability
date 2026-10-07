from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

from backend.app.settings import settings
from collectors.knox_sd import sync_knox_targets

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("/knox/status")
async def knox_integration_status() -> dict:
    jwt_path = settings.cpw_secrets_dir / "knox.jwt"
    has_jwt_file = jwt_path.is_file() and jwt_path.stat().st_size > 0
    has_env_jwt = bool((settings.knox_jwt or settings.hadoop_jwt or "").strip())
    targets = sync_knox_targets()
    return {
        "jwt_configured": has_jwt_file or has_env_jwt,
        "bearer_token_file": str(jwt_path),
        "bearer_token_file_ready": has_jwt_file,
        "knox_scrape_targets": len(targets),
        "prometheus_job": "nifi_knox",
        "note": "Primary metrics path remains kubectl federation; Knox is optional fallback.",
    }

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from fastapi import APIRouter

from backend.app.services.recommendations import recommend_for_issues

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


class RecommendIn(BaseModel):
    cluster_id: str = Field(..., min_length=1)
    product: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    namespace: str = Field(..., min_length=1)
    status: str = "unknown"
    issues: list[str] = Field(default_factory=list)
    metrics: dict[str, float | None] = Field(default_factory=dict)
    logs: dict[str, Any] = Field(default_factory=dict)


@router.post("")
async def post_recommendation(body: RecommendIn) -> dict[str, Any]:
    return await recommend_for_issues(body.model_dump())

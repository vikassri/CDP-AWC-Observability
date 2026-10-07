from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from backend.app.schemas import LogSearchIn
from backend.app.services.logs_search import search_logs

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/search")
async def logs_search(
    cluster: str | None = None,
    product: str | None = None,
    namespace: str | None = None,
    pod: str | None = None,
    q: str = "*",
    size: int = 50,
) -> dict[str, Any]:
    return await search_logs(
        LogSearchIn(cluster=cluster, product=product, namespace=namespace, pod=pod, q=q, size=size)
    )

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Incident
from backend.app.db.session import get_session
from backend.app.schemas import AlertFromLabelsIn, IncidentOut
from backend.app.services.logs_search import search_logs
from backend.app.schemas import LogSearchIn
from backend.app.services.prometheus_client import query_prometheus

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.post("/from-alert", response_model=IncidentOut)
async def create_from_alert(
    body: AlertFromLabelsIn,
    session: AsyncSession = Depends(get_session),
) -> IncidentOut:
    metric_snapshot: dict[str, Any] = {}
    if body.promql:
        try:
            metric_snapshot = await query_prometheus(body.promql)
        except Exception:  # noqa: BLE001
            metric_snapshot = {"error": "prometheus query failed"}

    logs = await search_logs(
        LogSearchIn(cluster=body.cluster_id, product=body.product, q="error OR exception", size=20)
    )
    excerpt = _format_log_hits(logs)

    incident = Incident(
        title=body.title,
        cluster_id=body.cluster_id,
        product=body.product,
        alert_labels=body.labels,
        metric_snapshot=metric_snapshot,
        log_excerpt=excerpt,
    )
    session.add(incident)
    await session.commit()
    await session.refresh(incident)
    return _to_out(incident)


@router.get("/{incident_id}", response_model=IncidentOut)
async def get_incident(
    incident_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> IncidentOut:
    result = await session.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return _to_out(incident)


def _format_log_hits(data: dict[str, Any]) -> str:
    hits = (data.get("hits") or {}).get("hits") or data.get("hits") or []
    if isinstance(hits, dict):
        hits = hits.get("hits") or []
    lines: list[str] = []
    for hit in hits[:15]:
        src = hit.get("_source") or hit
        body = src.get("body") or src.get("log") or src.get("message") or str(src)[:200]
        lines.append(str(body))
    return "\n".join(lines)


def _to_out(incident: Incident) -> IncidentOut:
    return IncidentOut(
        id=incident.id,
        title=incident.title,
        cluster_id=incident.cluster_id,
        product=incident.product,
        status=incident.status,
        alert_labels=incident.alert_labels,
        metric_snapshot=incident.metric_snapshot,
        log_excerpt=incident.log_excerpt,
    )

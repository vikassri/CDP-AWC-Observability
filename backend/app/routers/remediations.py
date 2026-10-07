from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config_loader import load_clusters, resolve_kubeconfig
from backend.app.db.models import Remediation
from backend.app.db.session import get_session
from backend.app.schemas import RemediationApproveIn, RemediationOut, RemediationPreviewIn
from backend.app.services.k8s_pool import delete_pod, rollout_restart_namespaced

ALLOWED_ACTIONS = frozenset({"rollout_restart", "delete_pod"})

router = APIRouter(prefix="/remediations", tags=["remediations"])


@router.post("/preview", response_model=RemediationOut)
async def preview_remediation(
    body: RemediationPreviewIn,
    session: AsyncSession = Depends(get_session),
) -> RemediationOut:
    if body.action_type not in ALLOWED_ACTIONS:
        raise HTTPException(status_code=400, detail=f"Action not allowed: {body.action_type}")

    preview = (
        f"Will {body.action_type} {body.kind} {body.namespace}/{body.name} "
        f"on cluster {body.cluster_id}"
    )
    row = Remediation(
        incident_id=body.incident_id,
        cluster_id=body.cluster_id,
        action_type=body.action_type,
        payload={
            "namespace": body.namespace,
            "name": body.name,
            "kind": body.kind,
        },
        preview=preview,
        status="pending",
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return _to_out(row)


@router.post("/{remediation_id}/approve", response_model=RemediationOut)
async def approve_remediation(
    remediation_id: uuid.UUID,
    body: RemediationApproveIn,
    session: AsyncSession = Depends(get_session),
) -> RemediationOut:
    row = await _get_row(session, remediation_id)
    if row.status != "pending":
        raise HTTPException(status_code=400, detail="Remediation not pending")
    row.status = "approved"
    row.approved_by = body.approved_by
    await session.commit()
    await session.refresh(row)
    return _to_out(row)


@router.post("/{remediation_id}/execute", response_model=RemediationOut)
async def execute_remediation(
    remediation_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> RemediationOut:
    row = await _get_row(session, remediation_id)
    if row.status != "approved":
        raise HTTPException(status_code=400, detail="Remediation must be approved first")

    cluster = _cluster(row.cluster_id)
    kc = resolve_kubeconfig(cluster)
    payload = row.payload
    try:
        if row.action_type == "rollout_restart":
            msg = await rollout_restart_namespaced(
                kc,
                cluster.context,
                payload["namespace"],
                payload["name"],
                payload.get("kind", "deployment"),
            )
        elif row.action_type == "delete_pod":
            msg = await delete_pod(kc, cluster.context, payload["namespace"], payload["name"])
        else:
            raise HTTPException(status_code=400, detail="Unknown action")
        row.status = "executed"
        row.result_message = msg
        row.executed_at = datetime.now(timezone.utc)
    except Exception as exc:  # noqa: BLE001
        row.status = "failed"
        row.result_message = str(exc)

    await session.commit()
    await session.refresh(row)
    return _to_out(row)


@router.get("", response_model=list[RemediationOut])
async def list_remediations(session: AsyncSession = Depends(get_session)) -> list[RemediationOut]:
    result = await session.execute(select(Remediation).order_by(Remediation.created_at.desc()).limit(100))
    return [_to_out(r) for r in result.scalars().all()]


async def _get_row(session: AsyncSession, remediation_id: uuid.UUID) -> Remediation:
    result = await session.execute(select(Remediation).where(Remediation.id == remediation_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Remediation not found")
    return row


def _cluster(cluster_id: str):
    for c in load_clusters():
        if c.id == cluster_id:
            return c
    raise HTTPException(status_code=404, detail="Cluster not found")


def _to_out(row: Remediation) -> RemediationOut:
    return RemediationOut(
        id=row.id,
        cluster_id=row.cluster_id,
        action_type=row.action_type,
        status=row.status,
        preview=row.preview,
        result_message=row.result_message,
    )

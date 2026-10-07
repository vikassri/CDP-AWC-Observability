from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import AlertAssignment, AlertState
from backend.app.db.session import get_session
from backend.app.services.alert_engine import alert_engine
from backend.app.services.alert_rules import append_custom_alert_rule, load_alert_rules
from backend.app.services.alerts_sync import sync_alert_definitions
from backend.app.services.collector_supervisor import supervisor
from backend.app.services.smtp_mailer import send_alert_email
from backend.app.settings import default_alert_recipients

router = APIRouter(prefix="/alerts", tags=["alerts"])


class AlertRuleCreateIn(BaseModel):
    alert: str = Field(..., min_length=1, max_length=128)
    expr: str = Field(..., min_length=1)
    product: str = Field(..., min_length=1)
    severity: str = "warning"
    summary: str = ""
    for_duration: str = "5m"
    emails: list[str] = Field(default_factory=list)
    enabled: bool = True


class AlertAssignmentIn(BaseModel):
    emails: list[str] = Field(default_factory=list)
    enabled: bool = True
    cluster_id: str = ""
    product: str = ""


class AlertRuleOut(BaseModel):
    rule_id: str
    alert: str
    product: str
    expr: str
    severity: str
    summary: str
    emails: list[str]
    enabled: bool
    firing: bool
    last_notified: str | None


@router.get("/rules", response_model=list[AlertRuleOut])
async def list_rules_with_assignments(session: AsyncSession = Depends(get_session)) -> list[AlertRuleOut]:
    rules = load_alert_rules()
    out: list[AlertRuleOut] = []
    for rule in rules:
        assignment = await session.get(AlertAssignment, rule.rule_id)
        state = await session.get(AlertState, rule.rule_id)
        emails = (
            list(assignment.emails)
            if assignment and assignment.emails
            else default_alert_recipients()
        )
        out.append(
            AlertRuleOut(
                rule_id=rule.rule_id,
                alert=rule.alert,
                product=rule.product,
                expr=rule.expr,
                severity=rule.labels.get("severity", "info"),
                summary=rule.annotations.get("summary", ""),
                emails=emails,
                enabled=assignment.enabled if assignment else True,
                firing=bool(state.firing) if state else False,
                last_notified=state.last_notified.isoformat() if state and state.last_notified else None,
            )
        )
    return out


@router.post("/rules", response_model=AlertRuleOut)
async def create_alert_rule(
    body: AlertRuleCreateIn,
    session: AsyncSession = Depends(get_session),
) -> AlertRuleOut:
    created = append_custom_alert_rule(
        alert=body.alert.strip(),
        expr=body.expr.strip(),
        product=body.product.strip().lower(),
        severity=body.severity.strip().lower(),
        summary=body.summary.strip(),
        for_duration=body.for_duration.strip(),
    )
    assignment = AlertAssignment(
        rule_id=created.rule_id,
        emails=body.emails,
        enabled=body.enabled,
        product=created.product,
    )
    session.add(assignment)
    await session.commit()
    return AlertRuleOut(
        rule_id=created.rule_id,
        alert=created.alert,
        product=created.product,
        expr=created.expr,
        severity=created.labels.get("severity", "warning"),
        summary=created.annotations.get("summary", ""),
        emails=body.emails or default_alert_recipients(),
        enabled=body.enabled,
        firing=False,
        last_notified=None,
    )


@router.put("/assignments/{rule_id}")
async def upsert_assignment(
    rule_id: str,
    body: AlertAssignmentIn,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    known = {r.rule_id for r in load_alert_rules()}
    if rule_id not in known:
        raise HTTPException(status_code=404, detail="Unknown alert rule")

    row = await session.get(AlertAssignment, rule_id)
    if not row:
        row = AlertAssignment(rule_id=rule_id)
        session.add(row)
    row.emails = body.emails
    row.enabled = body.enabled
    row.cluster_id = body.cluster_id
    row.product = body.product
    await session.commit()
    return {"status": "saved", "rule_id": rule_id}


@router.post("/evaluate")
async def evaluate_now() -> dict[str, str]:
    await alert_engine.evaluate_all()
    return {"status": "evaluated"}


@router.post("/test-email")
async def test_email(to: str) -> dict[str, str]:
    address = to.strip()
    if not address:
        raise HTTPException(status_code=400, detail="Missing to address")
    await send_alert_email(
        to_addresses=[address],
        subject="[CAO] SMTP test",
        body="CDP AWC Observability alert routing is configured correctly.",
    )
    return {"status": "sent", "to": address}


@router.get("")
async def list_alerts_legacy() -> dict[str, Any]:
    return {"rules": load_alert_rules(), "collectors": supervisor.status()}


@router.post("/sync")
async def sync_alerts() -> dict[str, Any]:
    return await sync_alert_definitions()

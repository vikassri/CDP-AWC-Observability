from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import AlertState
from backend.app.config_loader import load_clusters
from backend.app.services.service_overview import product_overview
from backend.app.services.smtp_mailer import send_alert_email
from backend.app.settings import default_alert_recipients

log = logging.getLogger(__name__)

ISSUE_PREFIX = "issue:"
_FLEET_PRODUCTS = ("nifi", "spark", "trino", "flink", "airflow")


def _primary_cluster_id(product: str) -> str | None:
    for cluster in load_clusters():
        if cluster.product == product:
            return cluster.id
    return None


def _issue_rule_id(product: str, cluster_id: str, namespace: str, name: str) -> str:
    raw = f"{product}|{cluster_id}|{namespace}|{name}"
    digest = hashlib.sha1(raw.encode()).hexdigest()[:16]
    return f"{ISSUE_PREFIX}{digest}"


async def evaluate_deployment_issue_alerts(session: AsyncSession) -> None:
    recipients = default_alert_recipients()
    if not recipients:
        return

    now = datetime.now(timezone.utc)
    active_ids: set[str] = set()

    for product in _FLEET_PRODUCTS:
        cluster_id = _primary_cluster_id(product)
        if not cluster_id:
            continue
        try:
            payload = await product_overview(product, cluster_id, lite=True)
        except Exception:  # noqa: BLE001
            log.exception("Deployment issue alert: %s overview failed", product)
            continue

        for dep in payload.get("deployments") or []:
            if not isinstance(dep, dict):
                continue
            status = str(dep.get("status") or "unknown")
            issues = dep.get("issues") or []
            issue_preview = issues[0] if issues else None
            if status == "healthy" and not issue_preview:
                continue

            namespace = str(dep.get("namespace") or "")
            name = str(dep.get("name") or namespace)
            rule_id = _issue_rule_id(product, cluster_id, namespace, name)
            active_ids.add(rule_id)

            state = await session.get(AlertState, rule_id)
            was_firing = state.firing if state else False
            if not state:
                state = AlertState(rule_id=rule_id, firing=False)
                session.add(state)

            state.last_evaluated = now
            state.firing = True

            if not was_firing:
                subject = f"[CAO ISSUE] {product.upper()} — {name}"
                body = (
                    f"Deployment issue detected\n\n"
                    f"Product: {product}\n"
                    f"Cluster: {cluster_id}\n"
                    f"Namespace: {namespace}\n"
                    f"Deployment: {name}\n"
                    f"Status: {status}\n"
                    f"Issue: {issue_preview or 'See CAO overview'}\n"
                    f"Time: {now.isoformat()}\n"
                )
                try:
                    await send_alert_email(to_addresses=recipients, subject=subject, body=body)
                    state.last_notified = now
                except Exception:  # noqa: BLE001
                    log.exception("Failed to send deployment issue alert for %s", rule_id)

    result = await session.execute(
        select(AlertState).where(AlertState.rule_id.like(f"{ISSUE_PREFIX}%"), AlertState.firing.is_(True))
    )
    for state in result.scalars():
        if state.rule_id in active_ids:
            continue
        state.firing = False
        state.last_evaluated = now
        subject = f"[CAO RESOLVED] Deployment issue cleared"
        body = f"Issue {state.rule_id} cleared at {now.isoformat()}\n"
        try:
            await send_alert_email(to_addresses=recipients, subject=subject, body=body)
            state.last_notified = now
        except Exception:  # noqa: BLE001
            log.exception("Failed to send deployment resolved alert for %s", state.rule_id)

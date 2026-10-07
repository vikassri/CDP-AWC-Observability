from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import AlertAssignment, AlertState
from backend.app.db.session import SessionLocal
from backend.app.services.alert_rules import load_alert_rules
from backend.app.services.deployment_issue_alerts import evaluate_deployment_issue_alerts
from backend.app.services.prometheus_client import query_prometheus
from backend.app.services.promql_helpers import normalize_promql
from backend.app.services.smtp_mailer import send_alert_email
from backend.app.settings import default_alert_recipients, settings

log = logging.getLogger(__name__)


class AlertEngine:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _loop(self) -> None:
        while True:
            try:
                await self.evaluate_all()
            except Exception:  # noqa: BLE001
                log.exception("Alert evaluation cycle failed")
            await asyncio.sleep(settings.alert_eval_interval_sec)

    async def evaluate_all(self) -> None:
        rules = load_alert_rules()
        prom_results = await asyncio.gather(
            *[self._is_firing(rule.expr) for rule in rules]
        )
        async with SessionLocal() as session:
            for rule, prom_firing in zip(rules, prom_results, strict=True):
                await self._evaluate_rule(session, rule, prom_firing)
            await evaluate_deployment_issue_alerts(session)
            await session.commit()

    async def _evaluate_rule(
        self, session: AsyncSession, rule, prom_firing: bool
    ) -> None:
        assignment = await session.get(AlertAssignment, rule.rule_id)
        defaults = default_alert_recipients()

        if assignment and not assignment.enabled:
            return
        if not assignment and not defaults:
            return

        recipients = (
            list(assignment.emails)
            if assignment and assignment.emails
            else list(defaults)
        )
        if not recipients:
            return

        firing = prom_firing
        state = await session.get(AlertState, rule.rule_id)
        now = datetime.now(timezone.utc)
        was_firing = state.firing if state else False

        if not state:
            state = AlertState(rule_id=rule.rule_id, firing=False)
            session.add(state)

        state.last_evaluated = now
        state.firing = firing

        if firing and not was_firing:
            subject = f"[CAO {rule.labels.get('severity', 'alert').upper()}] {rule.alert}"
            body = (
                f"Alert: {rule.alert}\n"
                f"Product: {rule.product}\n"
                f"Expression: {rule.expr}\n"
                f"Summary: {rule.annotations.get('summary', '')}\n"
                f"Description: {rule.annotations.get('description', '')}\n"
                f"Time: {now.isoformat()}\n"
            )
            await send_alert_email(to_addresses=recipients, subject=subject, body=body)
            state.last_notified = now
        elif not firing and was_firing:
            subject = f"[CAO RESOLVED] {rule.alert}"
            body = f"Alert {rule.alert} is no longer firing.\nTime: {now.isoformat()}\n"
            await send_alert_email(to_addresses=recipients, subject=subject, body=body)
            state.last_notified = now

    async def _is_firing(self, expr: str) -> bool:
        promql = normalize_promql(expr)
        try:
            result = await query_prometheus(promql)
        except Exception:  # noqa: BLE001
            return False
        data = result.get("data") or {}
        if data.get("resultType") != "vector":
            return False
        results = data.get("result") or []
        for series in results:
            value = series.get("value")
            if not value or len(value) < 2:
                continue
            try:
                if float(value[1]) > 0:
                    return True
            except (TypeError, ValueError):
                continue
        return False


alert_engine = AlertEngine()

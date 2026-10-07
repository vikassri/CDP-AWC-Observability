from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import AlertAssignment
from backend.app.services.alert_rules import load_alert_rules
from backend.app.settings import default_alert_recipients

log = logging.getLogger(__name__)


async def ensure_alert_assignments(session: AsyncSession) -> None:
    """Ensure every YAML rule is enabled with default recipients when unset."""
    recipients = default_alert_recipients()
    for rule in load_alert_rules():
        row = await session.get(AlertAssignment, rule.rule_id)
        if not row:
            session.add(
                AlertAssignment(
                    rule_id=rule.rule_id,
                    product=rule.product,
                    emails=list(recipients),
                    enabled=True,
                )
            )
            continue
        if recipients and not row.emails:
            row.emails = list(recipients)
        if not row.enabled and recipients:
            row.enabled = True
    await session.commit()
    if not recipients:
        log.warning(
            "ALERT_DEFAULT_RECIPIENTS is empty — configure SMTP recipients in Settings or .env"
        )

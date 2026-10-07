from __future__ import annotations

import logging
from email.message import EmailMessage

import aiosmtplib

from backend.app.settings import settings

log = logging.getLogger(__name__)


async def send_alert_email(*, to_addresses: list[str], subject: str, body: str) -> None:
    if not to_addresses:
        return
    if not settings.smtp_host:
        log.warning("SMTP not configured — skipping email to %s", to_addresses)
        return

    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = ", ".join(to_addresses)
    message["Subject"] = subject
    message.set_content(body)

    await aiosmtplib.send(
        message,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user or None,
        password=settings.smtp_password or None,
        start_tls=settings.smtp_start_tls,
        use_tls=settings.smtp_use_tls,
    )
    log.info("Alert email sent to %s", to_addresses)

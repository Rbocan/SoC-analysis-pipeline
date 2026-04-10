"""Email delivery using aiosmtplib."""
from __future__ import annotations

import asyncio
from email.message import EmailMessage
from pathlib import Path
from typing import Optional

import aiosmtplib
import structlog

from app.settings import settings

logger = structlog.get_logger()


async def send_report_email(
    recipients: list[str],
    subject: str,
    body_html: str,
    attachments: Optional[list[Path]] = None,
) -> bool:
    if not recipients:
        return False

    msg = EmailMessage()
    msg["From"] = settings.email_from
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.set_content("Please view this report in an HTML-capable email client.")
    msg.add_alternative(body_html, subtype="html")

    if attachments:
        for path in attachments:
            if path.exists():
                with open(path, "rb") as f:
                    msg.add_attachment(
                        f.read(),
                        maintype="application",
                        subtype="octet-stream",
                        filename=path.name,
                    )

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user or None,
            password=settings.smtp_password or None,
            start_tls=settings.smtp_port == 587,
        )
        logger.info("Email sent", recipients=recipients, subject=subject)
        return True
    except Exception as e:
        logger.error("Email failed", error=str(e), recipients=recipients)
        return False

from __future__ import annotations

import asyncio
import smtplib
import time
from email.message import EmailMessage

from backend import db
from backend.config import get_send_mode, smtp_config
from backend.textutil import has_unsubscribe, strip_subject, subject_line, truncate

_last_live_send = 0.0
_send_lock = asyncio.Lock()


class SendRefused(RuntimeError):
    pass


async def sender(lead: dict, draft: dict) -> dict:
    body = draft["body"]
    if not has_unsubscribe(body):
        raise SendRefused("refusing to send: critic-checked unsubscribe line is missing")

    mode = get_send_mode()
    dry_run = mode != "live"
    if dry_run:
        row = db.insert_message_sent(lead["id"], draft["id"], dry_run=True)
        db.update_lead(lead["id"], stage="SENT")
        lead["stage"] = "SENT"
        db.insert_run_log(
            lead_id=lead["id"],
            step="sender",
            provider="dry_run",
            model=None,
            latency_ms=0,
            input_summary=truncate(f"to={lead.get('email') or '(no email)'} draft_id={draft['id']}"),
            output="dry_run: logged, not delivered",
        )
        return row

    email_to = lead.get("email")
    if not email_to:
        raise SendRefused("refusing live send: no public email on this lead")

    smtp = smtp_config()
    if not smtp["host"] or not smtp["from_addr"]:
        raise SendRefused("live send requires SMTP_HOST and SMTP_FROM")

    async with _send_lock:
        global _last_live_send
        elapsed = time.monotonic() - _last_live_send
        if elapsed < 5:
            await asyncio.sleep(5 - elapsed)
        started = time.perf_counter()
        await asyncio.to_thread(_smtp_send, smtp, email_to, body, lead)
        _last_live_send = time.monotonic()
        latency_ms = int((time.perf_counter() - started) * 1000)

    row = db.insert_message_sent(lead["id"], draft["id"], dry_run=False)
    db.update_lead(lead["id"], stage="SENT")
    lead["stage"] = "SENT"
    db.insert_run_log(
        lead_id=lead["id"],
        step="sender",
        provider="smtp",
        model=smtp["host"],
        latency_ms=latency_ms,
        input_summary=truncate(f"to={email_to} draft_id={draft['id']}"),
        output="live send accepted by SMTP",
    )
    return row


def _smtp_send(smtp: dict, to_addr: str, body: str, lead: dict) -> None:
    msg = EmailMessage()
    msg["From"] = str(smtp["from_addr"])
    msg["To"] = to_addr
    msg["Subject"] = subject_line(body) or f"Quick note on {lead.get('project') or lead.get('repo')}"
    msg.set_content(strip_subject(body))
    with smtplib.SMTP(str(smtp["host"]), int(smtp["port"]), timeout=20) as client:
        client.starttls()
        if smtp["user"]:
            client.login(str(smtp["user"]), str(smtp["password"]))
        client.send_message(msg)

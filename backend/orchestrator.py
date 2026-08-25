from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

from backend import db
from backend.agents.closer import closer
from backend.agents.compressor import compressor
from backend.agents.copywriter import copywriter
from backend.agents.critic import critic
from backend.agents.reply_classifier import classify_reply
from backend.agents.researcher import researcher
from backend.agents.scout import scout
from backend.agents.sender import SendRefused, sender
from backend.agents.solver import solver
from backend.config import critic_max_retries, daily_lead_limit, get_send_mode
from backend.demo import load_demo
from backend.github_api import GitHubError
from backend.textutil import parse_json_object, truncate

STAGE_FOR_REPLY = {
    "interested": "MEETING_BOOKED",
    "objection": "NURTURE",
    "not_now": "CLOSED_LOST",
    "unsubscribe": "UNSUBSCRIBED",
}


def _event(kind: str, **payload: Any) -> dict[str, Any]:
    return {"type": kind, **payload}


def _think(message: str, **payload: Any) -> dict[str, Any]:
    return _event("status", message=message, **payload)


def _handle(lead: dict[str, Any] | None) -> str:
    return f"@{((lead or {}).get('github_handle') or 'someone')}"


async def run_pipeline(
    limit: int,
    *,
    campaign_id: int | None = None,
    problem: str | None = None,
    demo: bool = False,
) -> AsyncIterator[dict[str, Any]]:
    db.init_db()
    cap = min(max(1, limit), daily_lead_limit())
    if demo:
        yield _think("Loading a canned loop so you can see drafts without spending quota")
        await asyncio.sleep(0.4)
        leads = load_demo()
        yield _think(f"Found {len(leads)} people. Walking the board so you can open a draft")
        yield _event("scouted", count=len(leads), demo=True, campaign_id=campaign_id)
        for lead in leads:
            stage = str(lead.get("stage") or "").replace("_", " ").lower()
            yield _think(f"{_handle(lead)}: already {stage}")
            yield _event("lead", lead=lead, step="demo")
            await asyncio.sleep(0.32)
        yield _think("Done. The email is in the panel — or click View draft on a card")
        yield _event("done", count=len(leads), demo=True)
        return

    stated = (problem or "").strip()
    if stated:
        campaign = db.insert_problem(stated)
        campaign_id = campaign["id"]
    elif campaign_id:
        campaign = db.get_campaign(campaign_id)
        if not campaign:
            yield _event("error", message=f"campaign {campaign_id} not found")
            yield _event("done", count=0)
            return
        campaign = db.serialize_campaign(campaign) or campaign
    else:
        yield _event("error", message="a problem statement is required")
        yield _event("done", count=0)
        return

    stated = str((campaign or {}).get("problem") or stated).strip()
    if not stated:
        yield _event("error", message="campaign is missing a problem statement")
        yield _event("done", count=0)
        return

    remaining_today = max(0, daily_lead_limit() - db.count_leads_created_today())
    cap = min(cap, remaining_today) if remaining_today else 0
    if cap == 0:
        used = db.count_leads_created_today()
        limit = daily_lead_limit()
        yield _event(
            "error",
            message=f"daily lead limit reached ({used}/{limit}). Demo run still works, or wait until tomorrow.",
        )
        yield _event("done", count=0)
        return

    yield _think("Searching GitHub for people already hitting this", limit=cap, campaign_id=campaign_id)
    try:
        leads = await scout(campaign, cap)
    except GitHubError as exc:
        yield _think(f"GitHub search failed: {exc}")
        leads = []
    if not leads:
        yield _think("No one turned up on GitHub. Name the product and the failure (for example: Groq token cap)")
    else:
        yield _think(f"Found {len(leads)} people. Working through them one at a time")
    yield _event("scouted", count=len(leads), demo=False, campaign_id=campaign_id)

    for lead in leads:
        try:
            async for event in run_lead(lead["id"]):
                yield event
        except Exception as exc:  # noqa: BLE001 — keep the rest of the batch moving
            yield _think(f"{_handle(lead)}: hit an error, skipping to the next person")
            yield _event("error", message=str(exc), lead_id=lead["id"])
            db.insert_run_log(
                lead_id=lead["id"],
                step="orchestrator",
                provider=None,
                model=None,
                latency_ms=None,
                input_summary=str(exc),
                output="lead failed; continuing batch",
            )

    finals = [db.get_lead(item["id"]) for item in leads]
    n_draft = sum(
        1
        for row in finals
        if row
        and row.get("stage")
        in {"DRAFTED", "APPROVED", "SENT", "NEEDS_HUMAN_REVIEW", "MEETING_BOOKED"}
    )
    n_dq = sum(1 for row in finals if row and row.get("stage") == "DISQUALIFIED")
    if n_draft:
        yield _think("Done. Click a card with View draft to read the email")
    elif n_dq:
        yield _think("Done. Nobody cleared the fit bar, so Tavily and the email step never ran")
    else:
        yield _think("Done")
    yield _event("done", count=len(leads), demo=False)


async def run_lead(lead_id: int) -> AsyncIterator[dict[str, Any]]:
    lead = db.get_lead(lead_id)
    if not lead:
        yield _event("error", message=f"lead {lead_id} not found")
        return

    who = _handle(lead)
    yield _think(f"{who}: reading their README, issues, and recent commits")
    yield _event("lead", lead=lead, step="researcher")
    dump = await researcher(lead)
    lead = db.get_lead(lead_id)
    yield _event("lead", lead=lead, step="researcher")

    yield _think(f"{who}: compressing that into a short brief")
    yield _event("lead", lead=lead, step="compressor")
    brief = await compressor(lead, dump)
    lead = db.get_lead(lead_id)
    yield _event("lead", lead=lead, step="compressor", fit_score=brief.get("fit_score"))

    if lead["stage"] == "DISQUALIFIED":
        score = brief.get("fit_score")
        yield _think(f"{who}: fit {score} — not the same failure, skipping Tavily and the email")
        return

    yield _think(f"{who}: looking up a real solution for that pain")
    yield _event("lead", lead=lead, step="solver")
    brief = await solver(lead, brief)
    lead = db.get_lead(lead_id)
    yield _event("lead", lead=lead, step="solver")

    max_attempts = critic_max_retries()
    reasons: list[str] = []
    draft = None
    verdict = {"verdict": "FAIL", "reasons": ["no draft"]}
    for attempt in range(1, max_attempts + 1):
        if attempt == 1:
            yield _think(f"{who}: writing the outreach email")
        else:
            yield _think(f"{who}: critic sent it back — rewriting")
        yield _event("lead", lead=lead, step="copywriter", attempt=attempt)
        draft = await copywriter(lead, brief, critic_reasons=reasons or None)
        lead = db.get_lead(lead_id)
        yield _think(f"{who}: checking the draft against the brief")
        yield _event("lead", lead=lead, step="critic", attempt=attempt)
        verdict = await critic(lead, brief, draft)
        if verdict["verdict"] == "PASS":
            db.update_lead(lead_id, stage="APPROVED")
            lead = db.get_lead(lead_id)
            yield _event("lead", lead=lead, step="critic", verdict="PASS")
            break
        reasons = verdict["reasons"]
        yield _event(
            "lead",
            lead=db.get_lead(lead_id),
            step="critic",
            verdict="FAIL",
            reasons=reasons,
            attempt=attempt,
        )
    else:
        db.update_lead(lead_id, stage="NEEDS_HUMAN_REVIEW")
        lead = db.get_lead(lead_id)
        yield _think(f"{who}: draft never passed. parked for you")
        yield _event("lead", lead=lead, step="critic", verdict="FAIL", terminal=True)
        return

    try:
        mode = get_send_mode()
        if mode == "live":
            yield _think(f"{who}: draft passed. sending the email")
        else:
            yield _think(f"{who}: draft passed. logging a dry-run send")
        yield _event("lead", lead=lead, step="sender", send_mode=mode)
        await sender(lead, draft)
        lead = db.get_lead(lead_id)
        yield _event("lead", lead=lead, step="sender")
    except SendRefused as exc:
        db.update_lead(lead_id, stage="NEEDS_HUMAN_REVIEW")
        db.insert_run_log(
            lead_id=lead_id,
            step="sender",
            provider=get_send_mode(),
            model=None,
            latency_ms=0,
            input_summary=truncate(str(exc)),
            output="refused",
        )
        lead = db.get_lead(lead_id)
        yield _event("lead", lead=lead, step="sender", error=str(exc))


async def handle_reply(lead_id: int, body: str) -> dict[str, Any]:
    lead = db.get_lead(lead_id)
    if not lead:
        raise ValueError("lead not found")

    classification = await classify_reply(lead, body)
    category = classification["category"]
    db.insert_reply(lead_id, body, category)
    db.update_lead(lead_id, stage="REPLIED")

    closer_payload = None
    if category == "interested":
        briefs = db.briefs_for_lead(lead_id)
        brief = json.loads(briefs[-1]["brief_json"]) if briefs else {}
        try:
            closer_result = await closer(lead, brief, body)
            try:
                closer_payload = parse_json_object(closer_result["raw"])
            except ValueError:
                closer_payload = {
                    "email_body": closer_result["raw"],
                    "handoff_summary": closer_result["raw"],
                }
        except Exception as exc:  # noqa: BLE001 — still hand off if the LLM is down
            closer_payload = {
                "subject": f"Time with {brief.get('name') or lead.get('github_handle')}",
                "email_body": (
                    "Two windows that usually work: Tue 10:00 or Thu 14:00, your local time. "
                    "Reply with either and I'll send a calendar hold."
                ),
                "handoff_summary": (
                    f"{brief.get('name')} (@{lead.get('github_handle')}) replied interested. "
                    f"Pain: {brief.get('pain_signal')}. Angle: {brief.get('best_angle')}. "
                    f"Closer LLM unavailable ({exc})."
                ),
            }

    stage = STAGE_FOR_REPLY[category]
    db.update_lead(lead_id, stage=stage)
    lead = db.get_lead(lead_id)
    return {
        "lead": lead,
        "category": category,
        "rationale": classification.get("rationale"),
        "closer": closer_payload,
    }

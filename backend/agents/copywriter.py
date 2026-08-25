from __future__ import annotations

import json

from backend import db
from backend.providers import call_llm

SYSTEM = """You write short cold emails to developers. You are not a marketer.

Rules:
- 40-150 words in the body (not counting the Subject line)
- Direct, specific, human. No corporate jargon. Never use: synergy, leverage, circle back, going forward, unlock, delightful.
- The email MUST specifically reference the brief's pain_signal. That is the hook. No generic flattery.
- Then offer the brief's solution as the help. Every specific claim must come from the brief JSON (pain_signal, solution, best_angle, sources). Do not invent metrics, customers, or features.
- You may name an approach or tool only if it appears in brief.solution or brief.sources.
- Format exactly:

Subject: <short specific subject, not ALL CAPS, no exclamation points>

<email body>

- Do not use: guarantee, act now, $$$, or three or more exclamation points.
- One ask: a short reply, not a demo booking pitch.
The critic will reject missing opt-out language — only add an unsubscribe line if the review notes ask for it.
"""


async def copywriter(lead: dict, brief: dict, critic_reasons: list[str] | None = None) -> dict:
    campaign = db.campaign_for_lead(lead)
    user = "Brief JSON:\n" + json.dumps(brief, ensure_ascii=False, indent=2)
    if campaign:
        user += (
            "\n\nStated problem this run is about:\n"
            + json.dumps({"problem": campaign.get("problem")}, ensure_ascii=False)
        )
    if critic_reasons:
        user += "\n\nThe previous draft failed review. Fix every item:\n- " + "\n- ".join(critic_reasons)
    else:
        user += "\n\nDo not include an unsubscribe or opt-out line in this first draft."
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": user},
    ]
    result = await call_llm(
        "copywriter",
        messages,
        lead_id=lead["id"],
        temperature=0.5,
        max_tokens=500,
    )
    draft = db.insert_draft(lead["id"], _next_attempt(lead["id"]), result["content"].strip())
    db.update_lead(lead["id"], stage="DRAFTED")
    lead["stage"] = "DRAFTED"
    return draft


def _next_attempt(lead_id: int) -> int:
    existing = db.drafts_for_lead(lead_id)
    return len(existing) + 1

from __future__ import annotations

from backend.providers import call_llm
from backend.textutil import parse_json_object

CATEGORIES = ("interested", "objection", "not_now", "unsubscribe")

SYSTEM = """Classify a reply to a cold email. Return ONLY JSON:
{"category": "interested" | "objection" | "not_now" | "unsubscribe", "rationale": string}
- interested: wants to talk, asks a question, or is open to a meeting
- objection: engaged but pushing back on fit, timing, or the product
- not_now: polite deferral, maybe later
- unsubscribe: wants out, angry, or explicitly opting out
"""


def keyword_classify(body: str) -> str:
    lowered = body.lower()
    if any(w in lowered for w in ("unsubscribe", "stop emailing", "opt out", "opt-out", "don't contact")):
        return "unsubscribe"
    if any(w in lowered for w in ("not now", "maybe later", "next quarter", "busy")):
        return "not_now"
    if any(w in lowered for w in ("not a fit", "too expensive", "already have", "don't need")):
        return "objection"
    if any(
        w in lowered
        for w in ("interested", "let's talk", "lets talk", "book", "calendar", "sure", "tuesday", "can we talk")
    ):
        return "interested"
    return "not_now"


async def classify_reply(lead: dict, body: str) -> dict:
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": body},
    ]
    try:
        result = await call_llm(
            "reply_classifier",
            messages,
            lead_id=lead["id"],
            temperature=0.0,
            max_tokens=200,
        )
        parsed = parse_json_object(result["content"])
        category = str(parsed.get("category", "not_now")).lower().strip()
        rationale = str(parsed.get("rationale") or "")
        if category not in CATEGORIES:
            category = keyword_classify(body)
        return {"category": category, "rationale": rationale}
    except Exception as exc:  # noqa: BLE001 — keep simulate-reply usable without keys
        category = keyword_classify(body)
        return {"category": category, "rationale": f"keyword fallback ({exc})"}

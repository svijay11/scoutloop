from __future__ import annotations

import json
import re

from backend import db
from backend.providers import call_llm
from backend.textutil import has_unsubscribe, parse_json_object, strip_subject, subject_line, word_count

SPAM_PATTERNS = [
    (re.compile(r"\bguarantee\b", re.I), "spam-trigger: 'guarantee'"),
    (re.compile(r"\bact now\b", re.I), "spam-trigger: 'act now'"),
    (re.compile(r"\$\$\$"), "spam-trigger: '$$$'"),
    (re.compile(r"!{3,}"), "spam-trigger: 3+ exclamation points"),
]
JARGON = [
    (re.compile(r"\bsynergy\b", re.I), "tone: 'synergy'"),
    (re.compile(r"\bleverage\b", re.I), "tone: 'leverage'"),
    (re.compile(r"\bcircle back\b", re.I), "tone: 'circle back'"),
]

SYSTEM = """You are a strict editor for cold email. Score a draft against a brief.
Return ONLY JSON:
{
  "verdict": "PASS" or "FAIL",
  "reasons": [string]
}
Checklist:
1. Fact-grounding: every specific claim traces to a field in the brief (including solution / sources). Invented numbers, customers, or features = FAIL.
2. References the brief's pain_signal specifically, not generic flattery.
3. Offers the brief's solution, not a generic pitch.
4. Tone is direct. No corporate jargon.
If the draft passes, reasons must be [].
"""


def rule_check(body: str, brief: dict) -> list[str]:
    reasons: list[str] = []
    words = word_count(body)
    if words < 40:
        reasons.append(f"length: {words} words (minimum 40)")
    if words > 150:
        reasons.append(f"length: {words} words (maximum 150)")
    for pattern, label in SPAM_PATTERNS + JARGON:
        if pattern.search(body):
            reasons.append(label)
    subject = subject_line(body)
    if subject and subject.isupper() and any(c.isalpha() for c in subject):
        reasons.append("ALL CAPS subject line")
    if not has_unsubscribe(body):
        reasons.append("missing unsubscribe / opt-out line")
    pain = (brief.get("pain_signal") or "").strip().lower()
    body_l = strip_subject(body).lower()
    if pain:
        tokens = [t for t in re.split(r"\W+", pain) if len(t) > 4]
        hits = sum(1 for t in tokens if t in body_l)
        if tokens and hits < max(1, min(2, len(tokens) // 3)):
            reasons.append("does not reference pain_signal specifically")
    return reasons


async def critic(lead: dict, brief: dict, draft: dict) -> dict:
    body = draft["body"]
    rule_reasons = rule_check(body, brief)
    messages = [
        {"role": "system", "content": SYSTEM},
        {
            "role": "user",
            "content": (
                "Brief:\n"
                + json.dumps(brief, ensure_ascii=False, indent=2)
                + "\n\nDraft:\n"
                + body
            ),
        },
    ]
    llm_reasons: list[str] = []
    llm_verdict = "PASS"
    try:
        result = await call_llm("critic", messages, lead_id=lead["id"], temperature=0.0, max_tokens=400)
        parsed = parse_json_object(result["content"])
        llm_verdict = str(parsed.get("verdict", "FAIL")).upper()
        raw_reasons = parsed.get("reasons") or []
        if isinstance(raw_reasons, str):
            raw_reasons = [raw_reasons]
        llm_reasons = [str(r) for r in raw_reasons if str(r).strip()]
        if llm_verdict not in {"PASS", "FAIL"}:
            llm_verdict = "FAIL"
            llm_reasons.append("critic returned an invalid verdict")
    except Exception as exc:  # noqa: BLE001 — rules still apply if critic JSON is messy
        llm_verdict = "FAIL"
        llm_reasons = [f"critic parse error: {exc}"]

    reasons = list(dict.fromkeys(rule_reasons + (llm_reasons if llm_verdict == "FAIL" else [])))
    verdict = "PASS" if not reasons and llm_verdict == "PASS" else "FAIL"
    if rule_reasons:
        verdict = "FAIL"
        reasons = list(dict.fromkeys(rule_reasons + llm_reasons))

    db.update_draft(
        draft["id"],
        critic_verdict=verdict,
        critic_reasons=json.dumps(reasons) if reasons else "",
    )
    draft["critic_verdict"] = verdict
    draft["critic_reasons"] = json.dumps(reasons) if reasons else ""
    return {"verdict": verdict, "reasons": reasons, "draft": draft}

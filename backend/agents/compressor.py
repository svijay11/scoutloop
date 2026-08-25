from __future__ import annotations

import json

from backend import db
from backend.providers import call_llm
from backend.textutil import estimate_tokens, parse_json_object, truncate

BRIEF_KEYS = (
    "name",
    "github_handle",
    "project",
    "project_summary",
    "pain_signal",
    "signal_source",
    "best_angle",
    "contact_method",
    "fit_score",
)

SYSTEM = """You compress a raw GitHub research dump into a tight lead brief.
Return ONLY a JSON object with exactly these keys:
{
  "name": string,
  "github_handle": string,
  "project": string,
  "project_summary": string,      // one sentence
  "pain_signal": string,          // paraphrased; never a verbatim quote
  "signal_source": string,        // e.g. "issue #482 in repo X" or "README"
  "best_angle": string,           // one sentence
  "contact_method": "email" | "none_public",
  "fit_score": integer            // 0-100, how clearly THIS lead has the stated problem
}
Keep the whole object around 150-250 tokens. No markdown, no commentary.
contact_method is "email" only if a real public email is present in the dump (not a noreply address).
Paraphrase pain; do not copy issue text verbatim.
The dump may start with a MATCHED ISSUE — that issue is the primary evidence, not the README or unrelated recent issues.
fit_score is about the stated problem, not a generic ICP. Score 60-100 only if THIS person's own writing shows the same failure (same product or same class of breakage: token/context caps, batch jobs dying mid-run, lost work on restart). Nearby wording counts.
If the matched issue is a different problem, score below 40. Never copy the stated problem into pain_signal unless their text supports it.
best_angle is a one-sentence read of THEIR situation. Do not pitch a product — a later Tavily step writes the solution.
"""


def _normalize(raw: dict, lead: dict, dump: str) -> dict:
    contact = raw.get("contact_method")
    if contact not in {"email", "none_public"}:
        contact = "email" if lead.get("email") else "none_public"
    if not lead.get("email"):
        contact = "none_public"
    try:
        score = int(raw.get("fit_score", 0))
    except (TypeError, ValueError):
        score = 0
    score = max(0, min(100, score))
    brief = {
        "name": str(raw.get("name") or lead.get("name") or lead.get("github_handle")),
        "github_handle": str(raw.get("github_handle") or lead.get("github_handle")),
        "project": str(raw.get("project") or lead.get("project") or lead.get("repo")),
        "project_summary": str(raw.get("project_summary") or "").strip(),
        "pain_signal": str(raw.get("pain_signal") or "").strip(),
        "signal_source": str(raw.get("signal_source") or "").strip(),
        "best_angle": str(raw.get("best_angle") or "").strip(),
        "contact_method": contact,
        "fit_score": score,
    }
    if lead.get("email"):
        brief["email"] = lead["email"]
    missing = [k for k in BRIEF_KEYS if not str(brief.get(k, "")).strip() and k != "fit_score"]
    if missing:
        raise ValueError(f"brief missing fields: {', '.join(missing)}")
    return brief


async def compressor(lead: dict, dump: str) -> dict:
    campaign = db.campaign_for_lead(lead)
    problem = (campaign or {}).get("problem") or ""
    messages = [
        {"role": "system", "content": SYSTEM},
        {
            "role": "user",
            "content": (
                f"Stated problem we are hunting: {problem or '(none)'}\n"
                f"Public email on file: {lead.get('email') or 'none'}\n\n"
                f"RAW DUMP:\n{truncate(dump, 12000)}"
            ),
        },
    ]
    last_error = None
    brief = None
    for attempt in range(2):
        result = await call_llm("compressor", messages, lead_id=lead["id"], temperature=0.2, max_tokens=500)
        try:
            parsed = parse_json_object(result["content"])
            brief = _normalize(parsed, lead, dump)
            break
        except (ValueError, json.JSONDecodeError) as exc:
            last_error = exc
            messages = messages + [
                {"role": "assistant", "content": result["content"]},
                {
                    "role": "user",
                    "content": f"Invalid JSON ({exc}). Return only the JSON object, no markdown.",
                },
            ]
    if brief is None:
        raise RuntimeError(f"compressor failed to produce a brief: {last_error}")

    payload = json.dumps(brief, ensure_ascii=False)
    db.insert_brief(
        lead["id"],
        payload,
        estimate_tokens(dump),
        estimate_tokens(payload),
    )
    db.update_lead(
        lead["id"],
        stage="BRIEFED",
        fit_score=brief["fit_score"],
        name=brief.get("name") or lead.get("name"),
        project=brief.get("project") or lead.get("project"),
    )
    stage = "QUALIFIED" if brief["fit_score"] >= 60 else "DISQUALIFIED"
    db.update_lead(lead["id"], stage=stage, fit_score=brief["fit_score"])
    lead["stage"] = stage
    lead["fit_score"] = brief["fit_score"]
    return brief

from __future__ import annotations

import asyncio
import json

from backend import db
from backend.providers import call_llm
from backend.sourcefetch import format_search_hits, solution_research
from backend.textutil import estimate_tokens, parse_json_object, truncate

SYSTEM = """You propose a concrete solution for ONE GitHub lead who has a stated problem.

Return ONLY JSON:
{
  "solution": string,
  "best_angle": string,
  "sources": [{"title": string, "url": string}]
}

Rules:
- Ground the solution in the Tavily results. Do not invent products, vendors, or metrics that are not in those results or the brief.
- solution: 2-4 sentences. What would actually help THIS lead with THEIR pain_signal, given the stated problem.
- best_angle: one sentence for the outreach hook — their pain, then the offered approach.
- sources: 2-5 items, URLs copied from the Tavily results only.
- This is not competitor mapping. Do not list "alternatives to a company." Propose a fix for the pain in the brief.
"""


def _sources(raw: object, hits: list[dict]) -> list[dict[str, str]]:
    allowed = {str(h.get("url") or "").strip() for h in hits if h.get("url")}
    by_url = {str(h.get("url") or "").strip(): h for h in hits if h.get("url")}
    items = raw if isinstance(raw, list) else []
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        title = str(item.get("title") or "").strip()
        if not url or url not in allowed or url in seen:
            continue
        seen.add(url)
        if not title:
            title = str((by_url.get(url) or {}).get("title") or url)
        out.append({"title": title, "url": url})
        if len(out) >= 5:
            break
    if not out:
        for hit in hits[:3]:
            url = str(hit.get("url") or "").strip()
            if not url or url in seen:
                continue
            seen.add(url)
            out.append({"title": str(hit.get("title") or url), "url": url})
    return out


async def solver(lead: dict, brief: dict) -> dict:
    campaign = db.campaign_for_lead(lead) or {}
    problem = str(campaign.get("problem") or "").strip()
    pain = str(brief.get("pain_signal") or "").strip()
    hits_a, hits_b = await asyncio.to_thread(solution_research, problem, pain)
    hits = hits_a + hits_b
    market = "\n\n".join(
        [
            f"Stated problem: {problem}",
            f"This lead's pain_signal: {pain}",
            f"Project: {brief.get('project') or lead.get('repo')}",
            f"Project summary: {brief.get('project_summary') or ''}",
            "# Live search (Tavily)",
            format_search_hits("how to solve", hits_a),
            format_search_hits("approaches", hits_b),
        ]
    )
    messages = [
        {"role": "system", "content": SYSTEM},
        {
            "role": "user",
            "content": "Propose a solution for this lead.\n\n" + truncate(market, 8000),
        },
    ]
    last_error = None
    parsed = None
    for _attempt in range(2):
        result = await call_llm(
            "solver",
            messages,
            lead_id=lead["id"],
            temperature=0.2,
            max_tokens=900,
        )
        try:
            raw = parse_json_object(result["content"])
            parsed = {
                "solution": str(raw.get("solution") or "").strip(),
                "best_angle": str(raw.get("best_angle") or "").strip(),
                "sources": _sources(raw.get("sources"), hits),
            }
            if parsed["solution"] and parsed["best_angle"]:
                break
            raise ValueError("solver missing solution or best_angle")
        except (ValueError, json.JSONDecodeError) as exc:
            last_error = exc
            parsed = None
            messages = messages + [
                {"role": "assistant", "content": result["content"]},
                {
                    "role": "user",
                    "content": f"Invalid JSON ({exc}). Return ONLY the complete JSON object.",
                },
            ]
    if parsed is None:
        raise ValueError(f"solver returned invalid JSON: {last_error}")

    brief = dict(brief)
    brief["solution"] = parsed["solution"]
    brief["best_angle"] = parsed["best_angle"]
    brief["sources"] = parsed["sources"]
    payload = json.dumps(brief, ensure_ascii=False)
    db.update_latest_brief(lead["id"], payload, estimate_tokens(payload))
    return brief

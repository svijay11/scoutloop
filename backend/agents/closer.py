from __future__ import annotations

import json

from backend.providers import call_llm

SYSTEM = """You draft a meeting-time proposal and a handoff brief for a human to take over.
This is the ceiling — you do not negotiate contracts or close deals.
Return JSON:
{
  "subject": string,
  "email_body": string,          // 60-120 words, propose 2 concrete time windows in the next week (timezone-agnostic, e.g. "Tue 10:00 or Thu 14:00, their local time")
  "handoff_summary": string      // 4-6 sentences the human needs: who they are, the pain, the angle, any reply quotes, suggested next step
}
No pricing, no contracts, no "let's hop on a quick win". Direct and specific.
"""


async def closer(lead: dict, brief: dict, reply_body: str) -> dict:
    messages = [
        {"role": "system", "content": SYSTEM},
        {
            "role": "user",
            "content": (
                "Brief:\n"
                + json.dumps(brief, ensure_ascii=False, indent=2)
                + "\n\nInbound reply:\n"
                + reply_body
            ),
        },
    ]
    result = await call_llm("closer", messages, lead_id=lead["id"], temperature=0.4, max_tokens=700)
    return {
        "raw": result["content"],
        "provider": result["provider"],
        "model": result["model"],
    }

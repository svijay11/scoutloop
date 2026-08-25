from __future__ import annotations

import json
import time

from backend import db

DEMO_LEADS = [
    {
        "github_handle": "nivedita-labs",
        "repo": "nivedita-labs/token-shepherd",
        "name": "Nivedita Rao",
        "email": "nivedita@example.dev",
        "project": "token-shepherd",
        "stage": "SENT",
        "fit_score": 86,
        "brief": {
            "name": "Nivedita Rao",
            "github_handle": "nivedita-labs",
            "project": "token-shepherd",
            "project_summary": "A Python library that shards LLM context across models when a single window is not enough.",
            "pain_signal": "Open issue about embedding-batch jobs dying at the Groq token cap mid-run.",
            "signal_source": "issue #128 in nivedita-labs/token-shepherd",
            "best_angle": "Talk about surviving provider token ceilings without rewriting the batcher.",
            "contact_method": "email",
            "fit_score": 86,
            "email": "nivedita@example.dev",
        },
        "raw_tokens": 8420,
        "brief_tokens": 198,
        "drafts": [
            {
                "attempt_number": 1,
                "body": (
                    "Subject: Unlock your pipeline synergy\n\n"
                    "Hi Nivedita — circling back because I think we can leverage token-shepherd "
                    "to guarantee you never hit a rate limit again!!! We help teams like yours "
                    "act now and 10x embedding throughput across the board. Would love to hop on "
                    "a call this week to unlock the next level of your LLM stack.\n\n"
                    "Best,\nScoutloop"
                ),
                "critic_verdict": "FAIL",
                "critic_reasons": [
                    "spam-trigger: 'guarantee'",
                    "spam-trigger: 'act now'",
                    "spam-trigger: 3+ exclamation points",
                    "tone: 'synergy'",
                    "tone: 'leverage'",
                    "missing unsubscribe / opt-out line",
                    "does not reference pain_signal specifically",
                ],
            },
            {
                "attempt_number": 2,
                "body": (
                    "Subject: token-shepherd vs the embedding token cap\n\n"
                    "Nivedita — I saw issue #128 where embedding-batch jobs die at the Groq token "
                    "cap mid-run. That's the exact failure token-shepherd is trying to paper over "
                    "by sharding context.\n\n"
                    "We built a small router that fails over to a second provider when remaining "
                    "tokens hit zero, without rewriting the batcher. If that's useful I'll send "
                    "the 40-line snippet; if not, no thread.\n\n"
                    "If this isn't relevant, reply unsubscribe and I won't write again."
                ),
                "critic_verdict": "PASS",
                "critic_reasons": [],
            },
        ],
        "trace": [
            ("scout", "github", "search", 180, "icp=developers building LLM agent tooling", "token-shepherd stars=412 pain=True score=0.81"),
            ("researcher", "github", "rest", 640, "nivedita-labs nivedita-labs/token-shepherd", "README + issue #128 + 3 commits"),
            ("compressor", "groq", "llama-3.3-70b-versatile", 410, "raw dump 8420 tokens", '{"fit_score":86,"pain_signal":"embedding-batch jobs dying at the Groq token cap"}'),
            ("copywriter", "openrouter", "openai/gpt-oss-120b:free", 890, "brief JSON attempt 1", "Subject: Unlock your pipeline synergy..."),
            ("critic", "groq", "llama-3.3-70b-versatile", 280, "draft attempt 1", '{"verdict":"FAIL","reasons":["spam-trigger","missing unsubscribe"]}'),
            ("copywriter", "openrouter", "openai/gpt-oss-120b:free", 760, "brief JSON + critic reasons", "Subject: token-shepherd vs the embedding token cap..."),
            ("critic", "groq", "llama-3.3-70b-versatile", 265, "draft attempt 2", '{"verdict":"PASS","reasons":[]}'),
            ("sender", "dry_run", None, 0, "to=nivedita@example.dev", "dry_run: logged, not delivered"),
        ],
        "sent": True,
    },
    {
        "github_handle": "kai-okonkwo",
        "repo": "okonkwo/context-fuse",
        "name": "Kai Okonkwo",
        "email": "kai@okonkwo.dev",
        "project": "context-fuse",
        "stage": "APPROVED",
        "fit_score": 74,
        "brief": {
            "name": "Kai Okonkwo",
            "github_handle": "kai-okonkwo",
            "project": "context-fuse",
            "project_summary": "Merges retrieval chunks into a single prompt without blowing the window.",
            "pain_signal": "Rate-limit retries stampeded the OpenAI queue after a 429 on long-context fuse jobs.",
            "signal_source": "issue #44 in okonkwo/context-fuse",
            "best_angle": "Backoff and provider failover instead of retry storms.",
            "contact_method": "email",
            "fit_score": 74,
        },
        "raw_tokens": 5100,
        "brief_tokens": 172,
        "drafts": [
            {
                "attempt_number": 1,
                "body": (
                    "Subject: the 429 stampede in context-fuse\n\n"
                    "Kai — issue #44 describes retry storms after a 429 on long-context fuse jobs. "
                    "That's a provider-router problem, not a retrieval problem.\n\n"
                    "We run Groq and OpenRouter as a pair and fail over on 429 instead of retrying "
                    "the same key. Happy to share how the budget headers drive that, if useful.\n\n"
                    "If this isn't relevant, reply unsubscribe and I won't write again."
                ),
                "critic_verdict": "PASS",
                "critic_reasons": [],
            }
        ],
        "trace": [
            ("scout", "github", "search", 180, "icp=...", "context-fuse pain=True"),
            ("researcher", "github", "rest", 520, "kai-okonkwo/context-fuse", "README + issue #44"),
            ("compressor", "groq", "llama-3.3-70b-versatile", 390, "raw dump", '{"fit_score":74}'),
            ("copywriter", "openrouter", "openai/gpt-oss-120b:free", 700, "brief", "draft"),
            ("critic", "groq", "llama-3.3-70b-versatile", 240, "draft", '{"verdict":"PASS"}'),
        ],
        "sent": False,
    },
    {
        "github_handle": "mina-park",
        "repo": "park/agent-mailbox",
        "name": "Mina Park",
        "email": None,
        "project": "agent-mailbox",
        "stage": "DISQUALIFIED",
        "fit_score": 41,
        "brief": {
            "name": "Mina Park",
            "github_handle": "mina-park",
            "project": "agent-mailbox",
            "project_summary": "A toy IMAP client written to learn asyncio.",
            "pain_signal": "None related to LLM tooling — open issues are about charset decoding.",
            "signal_source": "README",
            "best_angle": "No outbound angle for a developer-tools ICP.",
            "contact_method": "none_public",
            "fit_score": 41,
        },
        "raw_tokens": 2200,
        "brief_tokens": 150,
        "drafts": [],
        "trace": [
            ("scout", "github", "search", 180, "icp=...", "agent-mailbox"),
            ("researcher", "github", "rest", 300, "park/agent-mailbox", "README"),
            ("compressor", "openrouter", "openai/gpt-oss-20b:free", 440, "raw dump", '{"fit_score":41}'),
        ],
        "sent": False,
    },
    {
        "github_handle": "theo-voss",
        "repo": "voss/rate-gate",
        "name": "Theo Voss",
        "email": "theo@voss.tools",
        "project": "rate-gate",
        "stage": "MEETING_BOOKED",
        "fit_score": 91,
        "brief": {
            "name": "Theo Voss",
            "github_handle": "theo-voss",
            "project": "rate-gate",
            "project_summary": "Per-key token accounting for multi-provider LLM proxies.",
            "pain_signal": "Hardcoded Groq RPM in config, which drifts every time Groq changes the plan.",
            "signal_source": "issue #7 in voss/rate-gate",
            "best_angle": "Read remaining-tokens headers instead of assuming a static quota.",
            "contact_method": "email",
            "fit_score": 91,
        },
        "raw_tokens": 6400,
        "brief_tokens": 188,
        "drafts": [
            {
                "attempt_number": 1,
                "body": (
                    "Subject: stop hardcoding Groq RPM in rate-gate\n\n"
                    "Theo — issue #7 is the static RPM number drifting every time Groq changes "
                    "the plan. We ran into the same thing and started reading "
                    "x-ratelimit-remaining-tokens off the response instead of guessing.\n\n"
                    "If you want the 30-line version of that tracker I'll send it.\n\n"
                    "If this isn't relevant, reply unsubscribe and I won't write again."
                ),
                "critic_verdict": "PASS",
                "critic_reasons": [],
            }
        ],
        "trace": [
            ("scout", "github", "search", 180, "icp=...", "rate-gate"),
            ("researcher", "github", "rest", 410, "voss/rate-gate", "README + issue #7"),
            ("compressor", "groq", "llama-3.3-70b-versatile", 360, "raw dump", '{"fit_score":91}'),
            ("copywriter", "openrouter", "openai/gpt-oss-120b:free", 680, "brief", "draft"),
            ("critic", "groq", "llama-3.3-70b-versatile", 250, "draft", '{"verdict":"PASS"}'),
            ("sender", "dry_run", None, 0, "to=theo@voss.tools", "dry_run: logged, not delivered"),
            ("reply_classifier", "groq", "llama-3.3-70b-versatile", 190, "yeah that header thing is exactly it — can we talk Tue?", '{"category":"interested"}'),
            ("closer", "openrouter", "openai/gpt-oss-120b:free", 720, "brief + reply", "Tue 10:00 or Thu 14:00"),
        ],
        "sent": True,
        "reply": {
            "body": "yeah that header thing is exactly it — can we talk Tuesday?",
            "category": "interested",
        },
    },
    {
        "github_handle": "ada-quist",
        "repo": "quist/window-saw",
        "name": "Ada Quist",
        "email": "ada@quist.io",
        "project": "window-saw",
        "stage": "QUALIFIED",
        "fit_score": 68,
        "brief": {
            "name": "Ada Quist",
            "github_handle": "ada-quist",
            "project": "window-saw",
            "project_summary": "Slices transcripts to fit a declared context window before they hit the model.",
            "pain_signal": "Context-window constant is still a magic number in settings.py.",
            "signal_source": "README",
            "best_angle": "Treat window size as a runtime header, not a config default.",
            "contact_method": "email",
            "fit_score": 68,
        },
        "raw_tokens": 3900,
        "brief_tokens": 160,
        "drafts": [],
        "trace": [
            ("scout", "github", "search", 180, "icp=...", "window-saw"),
            ("researcher", "github", "rest", 360, "quist/window-saw", "README"),
            ("compressor", "groq", "llama-3.3-70b-versatile", 400, "raw dump", '{"fit_score":68}'),
        ],
        "sent": False,
    },
    {
        "github_handle": "jonah-feld",
        "repo": "feld/tool-loop",
        "name": "Jonah Feld",
        "email": "jonah@feld.dev",
        "project": "tool-loop",
        "stage": "DRAFTED",
        "fit_score": 79,
        "brief": {
            "name": "Jonah Feld",
            "github_handle": "jonah-feld",
            "project": "tool-loop",
            "project_summary": "A hand-rolled agent loop that calls tools without LangGraph.",
            "pain_signal": "Open issue asking how to keep a critic pass from turning into an infinite rewrite loop.",
            "signal_source": "issue #19 in feld/tool-loop",
            "best_angle": "Hard-cap retries and park the lead for a human.",
            "contact_method": "email",
            "fit_score": 79,
        },
        "raw_tokens": 4700,
        "brief_tokens": 175,
        "drafts": [
            {
                "attempt_number": 1,
                "body": (
                    "Subject: critic retries on tool-loop\n\n"
                    "Jonah — issue #19 is the critic pass turning into an infinite rewrite loop. "
                    "We cap it at CRITIC_MAX_RETRIES and move the lead to NEEDS_HUMAN_REVIEW.\n\n"
                    "If this isn't relevant, reply unsubscribe and I won't write again."
                ),
                "critic_verdict": None,
                "critic_reasons": None,
            }
        ],
        "trace": [
            ("scout", "github", "search", 180, "icp=...", "tool-loop"),
            ("researcher", "github", "rest", 330, "feld/tool-loop", "README + issue #19"),
            ("compressor", "groq", "llama-3.3-70b-versatile", 370, "raw dump", '{"fit_score":79}'),
            ("copywriter", "openrouter", "openai/gpt-oss-120b:free", 640, "brief", "draft"),
        ],
        "sent": False,
    },
]


def load_demo() -> list[dict]:
    """Insert canned leads, briefs, drafts, and run_log rows. No live API calls."""
    db.init_db()
    created: list[dict] = []
    for spec in DEMO_LEADS:
        if db.lead_exists(spec["github_handle"], spec["repo"]):
            # already loaded — return existing row
            existing = [row for row in db.list_leads() if row["github_handle"] == spec["github_handle"]]
            if existing:
                created.append(existing[0])
            continue
        lead = db.insert_lead(
            github_handle=spec["github_handle"],
            repo=spec["repo"],
            name=spec.get("name"),
            email=spec.get("email"),
            project=spec.get("project"),
            stage=spec["stage"],
            fit_score=spec.get("fit_score"),
        )
        db.insert_brief(
            lead["id"],
            json.dumps(spec["brief"], ensure_ascii=False),
            spec.get("raw_tokens") or 0,
            spec.get("brief_tokens") or 0,
        )
        last_draft_id = None
        for draft in spec.get("drafts") or []:
            reasons = draft.get("critic_reasons")
            if isinstance(reasons, list):
                reasons = json.dumps(reasons)
            row = db.insert_draft(
                lead["id"],
                draft["attempt_number"],
                draft["body"],
                critic_verdict=draft.get("critic_verdict"),
                critic_reasons=reasons,
            )
            last_draft_id = row["id"]
        if spec.get("sent") and last_draft_id:
            db.insert_message_sent(lead["id"], last_draft_id, dry_run=True)
        if spec.get("reply"):
            db.insert_reply(lead["id"], spec["reply"]["body"], spec["reply"]["category"])
        for step, provider, model, latency, inp, out in spec.get("trace") or []:
            db.insert_run_log(
                lead_id=lead["id"],
                step=step,
                provider=provider,
                model=model,
                latency_ms=latency,
                input_summary=inp,
                output=out,
            )
        created.append(db.get_lead(lead["id"]))
        time.sleep(0)  # yield-friendly no-op; keeps import side-effect free
    return created

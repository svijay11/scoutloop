# Scoutloop

An outbound prospecting agent for developer tools. You state a problem. It finds GitHub developers already talking about that problem, researches the repo, looks up a solution, drafts a cold email, and **refuses to send** anything the critic wouldn't sign. Replies can be simulated from the dashboard; the ceiling is a meeting proposal plus a handoff brief.

Solo-use portfolio/demo. No auth, no accounts, no hosted deployment. Runs locally against your own API keys.

## What it does not do

- No closing, contracts, or autonomous negotiation.
- No live send unless `SEND_MODE=live` (default is dry-run: logged, not delivered).
- No posting on GitHub issues, PRs, or discussions. Outreach only goes to a public email on a profile.

## Setup

```bash
python3.12 -m venv .venv   # 3.9+ also works
source .venv/bin/activate
pip install -e .
cp .env.example .env          # fill in keys
scoutloop init
scoutloop doctor              # GitHub + Tavily + Groq + OpenRouter, plus rate-limit headers
scoutloop serve               # http://127.0.0.1:8787
```

In another terminal:

```bash
scoutloop run --problem "embedding-batch jobs die at the Groq token cap" --limit 8
# or, if quota is burned:
scoutloop run --demo
```

`scoutloop serve` builds the Vite frontend on first run if `frontend/dist` is missing, then serves the landing page, dashboard, and API together.

Frontend-only hot reload (API must already be on :8787):

```bash
cd frontend && npm install && npm run dev
```

## Environment

| Variable | Purpose |
| --- | --- |
| `OPENROUTER_API_KEY` | Copywriter / closer primary, compressor fallback |
| `GROQ_API_KEY` | Compressor / solver / critic / classifier primary |
| `GROQ_MODEL` | Groq model id (default `openai/gpt-oss-120b`; Llama 4 Scout was retired on Groq 2026-07-17) |
| `OPENROUTER_MODEL` | OpenRouter model id (default `nvidia/nemotron-3-ultra-550b-a55b:free`) |
| `GITHUB_TOKEN` | Scout + researcher (classic PAT with public repo read is enough) |
| `TAVILY_API_KEY` | Solution step — live search after a lead is researched |
| `SEND_MODE` | `dry_run` (default) or `live` |
| `DAILY_LEAD_LIMIT` | Cap for a single `scoutloop run` (default 20) |
| `CRITIC_MAX_RETRIES` | Hard cap on draft attempts (default 3) |
| `SMTP_*` | Only required for live send |

## The loop

1. **Problem** — you write the problem. No LLM. No Tavily.
2. **Scout** — GitHub repo + issue search for people already talking about that problem. Ranked by recency, stars, and issue overlap. No LLM.
3. **Researcher** — GitHub API: README, up to 5 open issues, 3 commits, public profile. No LLM.
4. **Compressor** — one LLM call → ~200-token JSON brief (`pain_signal`, `fit_score`). `fit_score >= 60` qualifies; otherwise the lead is terminal.
5. **Solver** — Tavily search on that lead's pain + the stated problem, then one LLM call writes `solution` / `best_angle` grounded in those hits.
6. **Copywriter** — one LLM call, 40–150 words, must reference `pain_signal` and offer `solution`.
7. **Critic** — rule checks (spam, length, jargon, unsubscribe line) plus an LLM pass/fail. Failures go back to the copywriter. Exceeding `CRITIC_MAX_RETRIES` parks the lead at `NEEDS_HUMAN_REVIEW`.
8. **Sender** — dry-run log by default. Live SMTP is 1 send / 5s and will refuse without the unsubscribe line.
9. **Reply classifier + closer** — dashboard “simulate reply”. Interested → meeting proposal + handoff summary. Stop there.

Provider routing lives in `backend/providers.py`. Primary 429 / 401 / missing key fails over to the other provider once. Rate-limit **headers** are stored and shown on the dashboard BudgetBar — limits are never hardcoded.

## Dashboard

Open http://127.0.0.1:8787/dashboard. State a problem, set a limit, run the loop. Click a card for the run receipt: every `run_log` row for that lead, expandable input/output, critic verdicts, and a simulate-reply box. That screen is the proof the loop ran.

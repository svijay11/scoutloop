from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys

import uvicorn

from backend import db
from backend.config import (
    FRONTEND_DIR,
    FRONTEND_DIST,
    github_token,
    groq_key,
    groq_model,
    openrouter_key,
    openrouter_model,
    tavily_key,
)
from backend.github_api import GitHubError, rate_limit
from backend.orchestrator import run_pipeline
from backend.providers import ProviderError, ping_provider


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="scoutloop", description="Outbound prospecting agent")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="create sqlite db + schema")
    sub.add_parser("serve", help="dashboard + landing at http://127.0.0.1:8787")
    sub.add_parser("doctor", help="check API keys and rate-limit headroom")

    run = sub.add_parser("run", help="scout + full pipeline")
    run.add_argument("--problem", help="the problem to find people talking about")
    run.add_argument("--limit", type=int, default=10)
    run.add_argument("--demo", action="store_true", help="offline canned data, no live API calls")

    args = parser.parse_args(argv)
    if args.cmd == "init":
        cmd_init()
    elif args.cmd == "serve":
        cmd_serve()
    elif args.cmd == "run":
        asyncio.run(cmd_run(args.problem, args.limit, args.demo))
    elif args.cmd == "doctor":
        asyncio.run(cmd_doctor())


def cmd_init() -> None:
    db.init_db()
    print(f"initialized {db.DB_PATH}")


def _build_frontend() -> None:
    if (FRONTEND_DIST / "index.html").exists():
        return
    if not (FRONTEND_DIR / "package.json").exists():
        print("frontend/ missing — API-only mode on :8787", file=sys.stderr)
        return
    npm = "npm"
    print("building frontend…")
    subprocess.run([npm, "install"], cwd=FRONTEND_DIR, check=True)
    subprocess.run([npm, "run", "build"], cwd=FRONTEND_DIR, check=True)


def cmd_serve() -> None:
    db.init_db()
    try:
        _build_frontend()
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"frontend build skipped: {exc}", file=sys.stderr)
    print("Scoutloop  http://127.0.0.1:8787")
    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=8787,
        reload=False,
        factory=False,
    )


async def cmd_run(problem: str | None, limit: int, demo: bool) -> None:
    db.init_db()
    if not demo and not (problem or "").strip():
        print("error: --problem is required (or pass --demo)", file=sys.stderr)
        sys.exit(2)
    print(f"run  problem={problem!r}  limit={limit}  demo={demo}")
    async for event in run_pipeline(limit, problem=problem, demo=demo):
        kind = event.get("type")
        if kind == "status":
            print(f"  {event.get('message')}")
        elif kind == "scouted":
            print(f"  scouted {event.get('count')} leads")
        elif kind == "lead":
            lead = event.get("lead") or {}
            handle = lead.get("github_handle", "?")
            stage = lead.get("stage", "")
            step = event.get("step", "")
            extra = ""
            if event.get("verdict"):
                extra = f"  {event['verdict']}"
            if event.get("fit_score") is not None:
                extra = f"  fit={event['fit_score']}"
            print(f"  [{lead.get('id')}] @{handle}  {step} → {stage}{extra}")
        elif kind == "error":
            print(f"  error: {event.get('message')}", file=sys.stderr)
        elif kind == "done":
            print(f"done  {event.get('count')} leads")


async def cmd_doctor() -> None:
    print("Scoutloop doctor\n")
    gh_ok = bool(github_token())
    print(f"  GITHUB_TOKEN         {'set' if gh_ok else 'MISSING'}")
    if gh_ok:
        try:
            data = await rate_limit()
            resources = data.get("resources") or {}
            for name in ("core", "search"):
                block = resources.get(name) or {}
                rem = block.get("remaining")
                limit = block.get("limit")
                print(f"    github {name:8}  remaining {rem}/{limit}")
        except GitHubError as exc:
            print(f"    github error: {exc}")
    else:
        print("    skip — no token")

    print(f"  TAVILY_API_KEY       {'set' if tavily_key() else 'MISSING'}")

    print(f"  GROQ_API_KEY         {'set' if groq_key() else 'MISSING'}")
    print(f"  GROQ_MODEL           {groq_model()}")
    try:
        snap = await ping_provider("groq")
        print(
            f"    groq               remaining req={snap.get('remaining_requests')}  "
            f"tokens={snap.get('remaining_tokens')}  "
            f"(limits from headers, not assumed)"
        )
    except ProviderError as exc:
        print(f"    groq error: {exc}")

    print(f"  OPENROUTER_API_KEY   {'set' if openrouter_key() else 'MISSING'}")
    print(f"  OPENROUTER_MODEL     {openrouter_model()}")
    try:
        snap = await ping_provider("openrouter")
        print(
            f"    openrouter         remaining req={snap.get('remaining_requests')}  "
            f"tokens={snap.get('remaining_tokens')}"
        )
    except ProviderError as exc:
        print(f"    openrouter error: {exc}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DB_PATH = ROOT / "scoutloop.db"
FRONTEND_DIR = ROOT / "frontend"
FRONTEND_DIST = FRONTEND_DIR / "dist"

GROQ_BASE = "https://api.groq.com/openai/v1"
OPENROUTER_BASE = "https://openrouter.ai/api/v1"
GITHUB_API = "https://api.github.com"

_send_mode_override: str | None = None


def getenv(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name, default)
    if value is None:
        return None
    value = value.strip()
    return value or default


def groq_key() -> str | None:
    return getenv("GROQ_API_KEY")


def openrouter_key() -> str | None:
    return getenv("OPENROUTER_API_KEY")


def groq_model() -> str:
    return getenv("GROQ_MODEL", "openai/gpt-oss-120b") or "openai/gpt-oss-120b"


def openrouter_model() -> str:
    return getenv("OPENROUTER_MODEL", "nvidia/nemotron-3-ultra-550b-a55b:free") or (
        "nvidia/nemotron-3-ultra-550b-a55b:free"
    )


def github_token() -> str | None:
    return getenv("GITHUB_TOKEN")


def tavily_key() -> str | None:
    return getenv("TAVILY_API_KEY")


def daily_lead_limit() -> int:
    raw = getenv("DAILY_LEAD_LIMIT", "20") or "20"
    try:
        return max(1, int(raw))
    except ValueError:
        return 20


def critic_max_retries() -> int:
    raw = getenv("CRITIC_MAX_RETRIES", "3") or "3"
    try:
        return max(1, int(raw))
    except ValueError:
        return 3


def get_send_mode() -> str:
    if _send_mode_override in {"dry_run", "live"}:
        return _send_mode_override
    mode = (getenv("SEND_MODE", "dry_run") or "dry_run").lower()
    return "live" if mode == "live" else "dry_run"


def set_send_mode(mode: str) -> str:
    global _send_mode_override
    normalized = "live" if mode == "live" else "dry_run"
    _send_mode_override = normalized
    return normalized


def smtp_config() -> dict[str, str | int]:
    return {
        "host": getenv("SMTP_HOST") or "",
        "port": int(getenv("SMTP_PORT", "587") or "587"),
        "user": getenv("SMTP_USER") or "",
        "password": getenv("SMTP_PASSWORD") or "",
        "from_addr": getenv("SMTP_FROM") or getenv("SMTP_USER") or "",
    }

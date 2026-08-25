from __future__ import annotations

import json
import re

EMAIL_RE = re.compile(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", re.I)
NOREPLY_MARKERS = ("noreply.github.com", "users.noreply.github.com")
UNSUBSCRIBE_RE = re.compile(r"unsub|opt[-\s]?out|stop writing|don't write again", re.I)


def estimate_tokens(text: str | None) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)


def truncate(text: str | None, limit: int = 1600) -> str:
    if not text:
        return ""
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def word_count(text: str) -> int:
    body = strip_subject(text)
    return len(body.split())


def strip_subject(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].lower().startswith("subject:"):
        rest = lines[1:]
        if rest and rest[0].strip() == "":
            rest = rest[1:]
        return "\n".join(rest).strip()
    return text.strip()


def subject_line(text: str) -> str | None:
    first = text.splitlines()[0] if text else ""
    if first.lower().startswith("subject:"):
        return first.split(":", 1)[1].strip()
    return None


def extract_emails(text: str | None) -> list[str]:
    if not text:
        return []
    found: list[str] = []
    for match in EMAIL_RE.findall(text):
        lower = match.lower()
        if any(marker in lower for marker in NOREPLY_MARKERS):
            continue
        if match not in found:
            found.append(match)
    return found


def parse_json_object(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        data = json.loads(text[start : end + 1])
        if isinstance(data, dict):
            return data
    raise ValueError("model output was not a JSON object")


def has_unsubscribe(text: str) -> bool:
    return bool(UNSUBSCRIBE_RE.search(text))

from __future__ import annotations

from backend.config import tavily_key
from backend.textutil import truncate


def tavily_search(query: str, max_results: int = 5) -> list[dict]:
    key = tavily_key()
    if not key:
        raise RuntimeError("TAVILY_API_KEY is not set — the solution step needs live search")
    from tavily import TavilyClient

    client = TavilyClient(api_key=key)
    data = client.search(query, max_results=max_results, search_depth="basic")
    hits: list[dict] = []
    for item in (data.get("results") or [])[:max_results]:
        title = str(item.get("title") or "").strip()
        url = str(item.get("url") or "").strip()
        snippet = str(item.get("content") or item.get("snippet") or "").strip()
        if not (title or url):
            continue
        hits.append({"title": title, "url": url, "snippet": snippet})
    return hits


def solution_research(problem: str, pain_signal: str) -> tuple[list[dict], list[dict]]:
    pain = (pain_signal or "").strip()
    stated = (problem or "").strip()
    q1 = f"{pain} how to solve".strip() if pain else f"{stated} how to solve"
    q2 = f"{stated} {pain}".strip() if pain else f"{stated} approaches"
    return tavily_search(q1, max_results=5), tavily_search(q2, max_results=5)


def format_search_hits(label: str, hits: list[dict]) -> str:
    if not hits:
        return f"## {label}\n(no results)"
    lines = [f"## {label}"]
    for i, hit in enumerate(hits, 1):
        lines.append(f"{i}. {hit.get('title') or '(untitled)'}")
        lines.append(f"   URL: {hit.get('url') or ''}")
        snippet = (hit.get("snippet") or "").replace("\n", " ")
        if snippet:
            lines.append(f"   {truncate(snippet, 280)}")
    return "\n".join(lines)

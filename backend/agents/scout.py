from __future__ import annotations

import re
import time
from datetime import datetime, timedelta, timezone

from backend import db
from backend.github_api import GitHubError, github_get, search
from backend.textutil import truncate

BOT_MARKERS = ("[bot]", "-bot", "dependabot", "github-actions")
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "building",
    "developers",
    "for",
    "in",
    "of",
    "on",
    "the",
    "this",
    "that",
    "who",
    "with",
    "when",
    "how",
    "to",
}
# Verbs and filler that turn GitHub AND-search into a zero-hit query.
GENERIC = STOPWORDS | {
    "about",
    "after",
    "again",
    "all",
    "also",
    "any",
    "anything",
    "because",
    "been",
    "before",
    "being",
    "can",
    "could",
    "die",
    "died",
    "dies",
    "dying",
    "everything",
    "from",
    "get",
    "gets",
    "getting",
    "got",
    "had",
    "has",
    "have",
    "into",
    "job",
    "jobs",
    "just",
    "keep",
    "keeps",
    "kept",
    "let",
    "lets",
    "lose",
    "loses",
    "losing",
    "lost",
    "make",
    "makes",
    "made",
    "mid",
    "more",
    "most",
    "need",
    "needed",
    "needs",
    "night",
    "nights",
    "our",
    "over",
    "per",
    "queue",
    "queues",
    "restart",
    "restarted",
    "restarting",
    "run",
    "running",
    "runs",
    "some",
    "something",
    "still",
    "than",
    "their",
    "them",
    "then",
    "these",
    "they",
    "those",
    "try",
    "tries",
    "trying",
    "under",
    "use",
    "used",
    "using",
    "via",
    "we",
    "while",
    "whole",
    "will",
    "without",
    "work",
    "worked",
    "working",
    "works",
}


def _days_ago(iso: str | None) -> int:
    if not iso:
        return 30
    try:
        pushed = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return 30
    delta = datetime.now(timezone.utc) - pushed.astimezone(timezone.utc)
    return max(0, delta.days)


def rank_score(*, stars: int, pushed_at: str | None, pain: bool, title_hits: int = 0) -> float:
    recency = max(0.0, 90 - _days_ago(pushed_at)) / 90.0
    if stars <= 2000:
        star_component = min(max(stars, 0), 2000) / 2000.0
    else:
        star_component = max(0.05, 1.0 - (stars - 2000) / 30000.0)
    pain_component = 1.0 if pain else 0.0
    title_component = min(max(title_hits, 0), 4) / 4.0
    return recency * 0.2 + star_component * 0.2 + pain_component * 0.25 + title_component * 0.35


def problem_keywords(problem: str) -> list[str]:
    tokens = [
        token
        for token in re.split(r"\W+", problem or "")
        if token and len(token) > 2 and token.lower() not in GENERIC
    ]
    seen: set[str] = set()
    distinctive: list[str] = []
    for token in tokens:
        key = token.lower()
        if key in seen:
            continue
        seen.add(key)
        distinctive.append(token)
    return distinctive[:4]


def problem_terms(problem: str) -> str:
    terms = problem_keywords(problem)
    return " ".join(terms) if terms else (problem or "").strip()


def _has_word(text: str, word: str) -> bool:
    token = (word or "").strip()
    if not token:
        return False
    return re.search(rf"(?<![a-z0-9]){re.escape(token.lower())}(?![a-z0-9])", (text or "").lower()) is not None


def _keyword_hits(text: str, keywords: list[str]) -> list[str]:
    hits: list[str] = []
    seen: set[str] = set()
    for token in keywords:
        key = token.lower()
        if key in seen:
            continue
        if _has_word(text, token):
            seen.add(key)
            hits.append(token)
    return hits


def _product_tokens(keywords: list[str]) -> list[str]:
    skip = GENERIC | {
        "api",
        "batch",
        "client",
        "data",
        "embedding",
        "embeddings",
        "error",
        "errors",
        "file",
        "files",
        "issue",
        "issues",
        "limit",
        "limits",
        "model",
        "models",
        "request",
        "requests",
        "server",
        "token",
        "tokens",
    }
    return [token for token in keywords if token.lower() not in skip]


def _issue_text(issue: dict) -> str:
    title = str(issue.get("title") or "")
    body = str(issue.get("body") or "")[:4000]
    return f"{title}\n{body}"


def _issue_relevant(issue: dict, keywords: list[str]) -> bool:
    text = _issue_text(issue)
    if not text.strip():
        return False
    products = _product_tokens(keywords)
    if products and not any(_has_word(text, token) for token in products):
        return False
    hard_fail = ("limit", "limits", "cap", "capped", "quota", "timeout", "429", "ratelimit", "oom")
    return any(_has_word(text, word) for word in hard_fail)


def _is_bot_login(login: str) -> bool:
    lowered = login.lower()
    if any(marker in lowered for marker in BOT_MARKERS):
        return True
    return lowered.endswith("[bot]")


def _is_person_user(user: dict | None) -> bool:
    if not user:
        return False
    login = str(user.get("login") or "").strip()
    if not login or _is_bot_login(login):
        return False
    owner_type = str(user.get("type") or "User")
    return owner_type not in {"Organization", "Bot"}


def _is_person_owner(repo: dict) -> bool:
    return _is_person_user(repo.get("owner") or {})


def _within_star_range(repo: dict, *, lo: int = 5, hi: int = 5000) -> bool:
    if repo.get("stargazers_count") is None:
        return True
    stars = int(repo.get("stargazers_count") or 0)
    return lo <= stars <= hi


def _fresh(repo: dict, *, days: int = 90) -> bool:
    if not repo.get("pushed_at"):
        return True
    return _days_ago(repo.get("pushed_at")) <= days


def _not_fork(repo: dict) -> bool:
    return not bool(repo.get("fork"))


def _repo_full_name_from_issue(issue: dict) -> str:
    extra = issue.get("repository")
    if isinstance(extra, dict) and extra.get("full_name"):
        return str(extra["full_name"]).strip()
    repo_url = str(issue.get("repository_url") or "")
    if "/repos/" in repo_url:
        return repo_url.rsplit("/repos/", 1)[1].strip()
    html = str(issue.get("html_url") or "")
    parts = html.split("/")
    if "github.com" in html and len(parts) >= 5:
        return f"{parts[3]}/{parts[4]}"
    return ""


async def _hydrate(repo: dict) -> dict:
    if repo.get("stargazers_count") is not None and (repo.get("owner") or {}).get("type"):
        return repo
    full_name = (repo.get("full_name") or "").strip()
    if not full_name:
        return repo
    try:
        return (await github_get(f"/repos/{full_name}")).json()
    except GitHubError:
        return repo


async def _try_search(
    kind: str, query: str, *, sort: str | None = None, per_page: int = 20
) -> tuple[list[dict], str | None]:
    try:
        return await search(kind, query, sort=sort, per_page=per_page), None
    except GitHubError as exc:
        return [], str(exc)


def _issue_queries(keywords: list[str]) -> list[str]:
    queries: list[str] = []
    products = _product_tokens(keywords)
    product = products[0] if products else None
    if len(keywords) >= 3:
        queries.append(f"{' '.join(keywords[:3])} is:issue")
    if product:
        rest = [token for token in keywords if token.lower() != product.lower()][:2]
        if rest:
            queries.append(f"{product} {' '.join(rest)} is:issue")
        queries.append(
            f"{product} (limit OR cap OR quota OR timeout OR 429 OR token) is:issue"
        )
    elif len(keywords) >= 2:
        queries.append(f"{' '.join(keywords[:2])} is:issue")
    seen: set[str] = set()
    unique: list[str] = []
    for query in queries:
        if query in seen:
            continue
        seen.add(query)
        unique.append(query)
    return unique


def _repo_queries(keywords: list[str], since: str) -> list[str]:
    queries: list[str] = []
    if len(keywords) >= 2:
        queries.append(f"{' '.join(keywords[:3])} fork:false")
        queries.append(f"{' '.join(keywords[:2])} language:python fork:false stars:5..5000")
    if keywords:
        queries.append(f"{keywords[0]} language:python fork:false stars:10..5000 pushed:>{since}")
    seen: set[str] = set()
    unique: list[str] = []
    for query in queries:
        if query in seen:
            continue
        seen.add(query)
        unique.append(query)
    return unique


def _candidate(
    *,
    handle: str,
    repo: dict,
    pain: bool,
    source_issue: str | None = None,
    issue_title: str | None = None,
    title_hits: int = 0,
) -> dict:
    full_name = (repo.get("full_name") or "").strip()
    return {
        "github_handle": handle,
        "repo": full_name,
        "project": repo.get("name") or (full_name.split("/")[-1] if full_name else handle),
        "stars": int(repo.get("stargazers_count") or 0),
        "pushed_at": repo.get("pushed_at"),
        "pain": pain,
        "source_issue": (source_issue or "").strip() or None,
        "issue_title": (issue_title or "").strip(),
        "score": rank_score(
            stars=int(repo.get("stargazers_count") or 0),
            pushed_at=repo.get("pushed_at"),
            pain=pain,
            title_hits=title_hits,
        ),
        "description": repo.get("description") or "",
    }


async def scout(campaign: dict, limit: int) -> list[dict]:
    started = time.perf_counter()
    campaign_id = campaign["id"]
    payload = db.serialize_campaign(campaign) or {}
    problem = str(payload.get("problem") or "").strip()
    keywords = problem_keywords(problem)
    if not keywords:
        raise ValueError("campaign is missing a problem statement")
    since = (datetime.now(timezone.utc) - timedelta(days=90)).strftime("%Y-%m-%d")

    errors: list[str] = []
    ran_queries: list[str] = []
    ranked: list[dict] = []
    seen_people: set[str] = set()
    seen_pairs: set[str] = set()
    repo_cache: dict[str, dict] = {}
    pool_cap = max(limit * 5, 15)

    def add_candidate(item: dict) -> None:
        handle = (item.get("github_handle") or "").strip()
        repo_name = (item.get("repo") or "").strip()
        if not handle or not repo_name:
            return
        person_key = handle.lower()
        pair_key = f"{person_key}:{repo_name.lower()}"
        if person_key in seen_people or pair_key in seen_pairs:
            return
        seen_people.add(person_key)
        seen_pairs.add(pair_key)
        ranked.append(item)

    async def hydrate_cached(full_name: str, extra: dict) -> dict:
        key = full_name.lower()
        if key not in repo_cache:
            repo_cache[key] = await _hydrate({"full_name": full_name, **extra})
        return repo_cache[key]

    for query in _issue_queries(keywords):
        ran_queries.append(f"issues:{query}")
        issues, error = await _try_search("issues", query, per_page=30)
        if error:
            errors.append(error)
            continue
        for issue in issues:
            if issue.get("pull_request"):
                continue
            if not _issue_relevant(issue, keywords):
                continue
            user = issue.get("user") or {}
            if not _is_person_user(user):
                continue
            full_name = _repo_full_name_from_issue(issue)
            if not full_name:
                continue
            extra = issue.get("repository") if isinstance(issue.get("repository"), dict) else {}
            repo = await hydrate_cached(full_name, extra)
            title = str(issue.get("title") or "")
            add_candidate(
                _candidate(
                    handle=str(user.get("login") or "").strip(),
                    repo=repo,
                    pain=True,
                    source_issue=str(issue.get("html_url") or "").strip() or None,
                    issue_title=title,
                    title_hits=len(_keyword_hits(title, keywords)),
                )
            )
        if len(ranked) >= pool_cap:
            break

    if len(ranked) < limit:
        for query in _repo_queries(keywords, since):
            ran_queries.append(f"repos:{query}")
            repos, error = await _try_search("repositories", query, sort="updated", per_page=30)
            if error:
                errors.append(error)
                continue
            for repo in repos[:40]:
                full_name = (repo.get("full_name") or "").strip()
                if not full_name:
                    continue
                repo = await hydrate_cached(full_name, repo)
                if not _is_person_owner(repo) or not _not_fork(repo):
                    continue
                if not _within_star_range(repo) or not _fresh(repo):
                    continue
                owner = ((repo.get("owner") or {}).get("login") or "").strip()
                add_candidate(_candidate(handle=owner, repo=repo, pain=False))
            if len(ranked) >= pool_cap:
                break

    if not ranked and errors:
        raise GitHubError(errors[0])

    ranked.sort(key=lambda item: item["score"], reverse=True)

    inserted: list[dict] = []
    latency_ms = int((time.perf_counter() - started) * 1000)
    for candidate in ranked:
        if len(inserted) >= limit:
            break
        if db.lead_exists(candidate["github_handle"], candidate["repo"], campaign_id):
            continue
        lead = db.insert_lead(
            github_handle=candidate["github_handle"],
            repo=candidate["repo"],
            project=candidate["project"],
            stage="NEW",
            campaign_id=campaign_id,
            source_issue=candidate.get("source_issue"),
        )
        issue_bit = candidate.get("issue_title") or candidate.get("source_issue") or ""
        db.insert_run_log(
            lead_id=lead["id"],
            step="scout",
            provider="github",
            model="search",
            latency_ms=latency_ms,
            input_summary=truncate(f"problem={problem} queries=" + " | ".join(ran_queries)),
            output=truncate(
                f"{candidate['github_handle']} {candidate['repo']} stars={candidate['stars']} "
                f"pain={candidate['pain']} score={candidate['score']:.3f} {issue_bit}"
            ),
        )
        inserted.append(lead)

    return inserted

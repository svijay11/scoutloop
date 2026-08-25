from __future__ import annotations

import re
import time

from backend import db
from backend.github_api import github_get
from backend.textutil import extract_emails, truncate


def _issue_body(issue: dict) -> str:
    body = (issue.get("body") or "").strip()
    return body[:1200]


def _format_issue(issue: dict) -> str:
    number = issue.get("number")
    title = issue.get("title") or ""
    return f"## #{number} {title}\n{_issue_body(issue)}"


def _issue_number(source_issue: str | None) -> int | None:
    text = (source_issue or "").strip()
    if not text:
        return None
    match = re.search(r"/(?:issues|pull)/(\d+)", text)
    if match:
        return int(match.group(1))
    match = re.search(r"#(\d+)\s*$", text)
    if match:
        return int(match.group(1))
    if text.isdigit():
        return int(text)
    return None


async def researcher(lead: dict) -> str:
    started = time.perf_counter()
    repo = lead["repo"]
    handle = lead["github_handle"]
    chunks: list[str] = []
    seen_issues: set[int] = set()

    profile: dict = {}
    try:
        profile = (await github_get(f"/users/{handle}")).json()
    except Exception as exc:  # noqa: BLE001 — keep the dump going if profile 404s
        chunks.append(f"# Profile\nhandle: {handle}\n(profile fetch failed: {exc})\n")
        profile = {}

    name = profile.get("name") or handle
    email = profile.get("email")
    bio = profile.get("bio") or ""
    blog = profile.get("blog") or ""
    chunks.append(
        "\n".join(
            [
                "# Profile",
                f"handle: {handle}",
                f"name: {name}",
                f"bio: {bio}",
                f"email: {email or ''}",
                f"blog: {blog}",
                f"company: {profile.get('company') or ''}",
            ]
        )
    )

    repo_data: dict = {}
    try:
        repo_data = (await github_get(f"/repos/{repo}")).json()
    except Exception as exc:  # noqa: BLE001
        chunks.append(f"\n# Repo\n{repo}\n(fetch failed: {exc})")

    if repo_data:
        chunks.append(
            "\n".join(
                [
                    "# Repo",
                    f"full_name: {repo_data.get('full_name') or repo}",
                    f"description: {repo_data.get('description') or ''}",
                    f"stars: {repo_data.get('stargazers_count') or 0}",
                    f"language: {repo_data.get('language') or ''}",
                    f"pushed_at: {repo_data.get('pushed_at') or ''}",
                    f"homepage: {repo_data.get('homepage') or ''}",
                ]
            )
        )

    matched_number = _issue_number(lead.get("source_issue"))
    if matched_number:
        try:
            matched = (await github_get(f"/repos/{repo}/issues/{matched_number}")).json()
            seen_issues.add(int(matched.get("number") or matched_number))
            body = (matched.get("body") or "").strip()[:2500]
            chunks.append(
                "\n".join(
                    [
                        "# Matched issue (why this person)",
                        f"url: {matched.get('html_url') or lead.get('source_issue') or ''}",
                        f"## #{matched.get('number')} {matched.get('title') or ''}",
                        body or "(empty body)",
                    ]
                )
            )
        except Exception as exc:  # noqa: BLE001
            chunks.append(
                f"# Matched issue (why this person)\n{lead.get('source_issue')}\n(fetch failed: {exc})"
            )

    authored: list[str] = []
    try:
        theirs = (
            await github_get(
                f"/repos/{repo}/issues",
                params={"state": "all", "creator": handle, "per_page": 5},
            )
        ).json()
        for issue in theirs:
            if "pull_request" in issue:
                continue
            number = int(issue.get("number") or 0)
            if not number or number in seen_issues:
                continue
            seen_issues.add(number)
            authored.append(_format_issue(issue))
    except Exception as exc:  # noqa: BLE001
        authored.append(f"(authored-issues fetch failed: {exc})")
    if authored:
        chunks.append("# Issues opened by this person\n" + "\n\n".join(authored))

    readme = ""
    try:
        response = await github_get(
            f"/repos/{repo}/readme",
            accept="application/vnd.github.raw",
        )
        readme = response.text[:2500]
    except Exception as exc:  # noqa: BLE001
        readme = f"(readme fetch failed: {exc})"
    chunks.append(f"# README\n{readme}")

    issues_blob = []
    try:
        issues = (await github_get(f"/repos/{repo}/issues", params={"state": "open", "per_page": 5})).json()
        for issue in issues:
            if "pull_request" in issue:
                continue
            number = int(issue.get("number") or 0)
            if number in seen_issues:
                continue
            seen_issues.add(number)
            issues_blob.append(_format_issue(issue))
            if len(issues_blob) >= 3:
                break
    except Exception as extra_exc:  # noqa: BLE001
        issues_blob.append(f"(issues fetch failed: {extra_exc})")
    chunks.append("# Other open issues\n" + ("\n\n".join(issues_blob) if issues_blob else "(none)"))

    commits_blob = []
    try:
        commits = (await github_get(f"/repos/{repo}/commits", params={"per_page": 3})).json()
        for commit in commits:
            sha = (commit.get("sha") or "")[:7]
            message = ((commit.get("commit") or {}).get("message") or "").split("\n", 1)[0]
            author_email = ((commit.get("commit") or {}).get("author") or {}).get("email")
            commits_blob.append(f"- {sha} {message}")
            if author_email and not email:
                email = author_email
    except Exception as exc:  # noqa: BLE001
        commits_blob.append(f"(commits fetch failed: {exc})")
    chunks.append("# Recent commits\n" + "\n".join(commits_blob))

    dump = "\n\n".join(chunks)
    found_emails = extract_emails(dump)
    if found_emails:
        email = found_emails[0]
    if email and any(marker in email.lower() for marker in ("noreply.github.com",)):
        email = None

    db.update_lead(
        lead["id"],
        stage="RESEARCHED",
        name=name,
        email=email,
        project=lead.get("project") or (repo.split("/")[-1] if repo else None),
    )
    latency_ms = int((time.perf_counter() - started) * 1000)
    db.insert_run_log(
        lead_id=lead["id"],
        step="researcher",
        provider="github",
        model="rest",
        latency_ms=latency_ms,
        input_summary=truncate(f"{handle} {repo} {lead.get('source_issue') or ''}"),
        output=truncate(dump, 2400),
    )
    lead.update({"name": name, "email": email, "stage": "RESEARCHED"})
    return dump

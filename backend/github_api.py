from __future__ import annotations

import httpx

from backend.config import GITHUB_API, github_token

SEARCH_TIMEOUT = 30.0
REST_TIMEOUT = 20.0


class GitHubError(RuntimeError):
    pass


def _headers() -> dict[str, str]:
    token = github_token()
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "scoutloop",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


async def github_get(
    path: str,
    *,
    params: dict | None = None,
    accept: str | None = None,
    timeout: float = REST_TIMEOUT,
) -> httpx.Response:
    headers = _headers()
    if accept:
        headers["Accept"] = accept
    url = path if path.startswith("http") else f"{GITHUB_API}{path}"
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(url, headers=headers, params=params)
    if response.status_code == 403 and "rate limit" in response.text.lower():
        raise GitHubError("GitHub rate limit hit. Wait a minute, or run `scoutloop run --demo`.")
    if response.status_code >= 400:
        raise GitHubError(f"GitHub {response.status_code}: {response.text[:300]}")
    return response


async def search(kind: str, query: str, *, sort: str | None = None, per_page: int = 30) -> list[dict]:
    params: dict[str, str | int] = {"q": query, "per_page": per_page}
    if sort:
        params["sort"] = sort
        params["order"] = "desc"
    response = await github_get(f"/search/{kind}", params=params, timeout=SEARCH_TIMEOUT)
    data = response.json()
    return list(data.get("items") or [])


async def rate_limit() -> dict:
    response = await github_get("/rate_limit")
    return response.json()

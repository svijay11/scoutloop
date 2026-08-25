from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from backend import db
from backend.config import (
    GROQ_BASE,
    OPENROUTER_BASE,
    groq_key,
    groq_model,
    openrouter_key,
    openrouter_model,
)
from backend.textutil import truncate


def _routes() -> dict[str, tuple[str, str]]:
    groq = f"groq/{groq_model()}"
    openrouter = f"openrouter/{openrouter_model()}"
    # Fast structured steps on Groq; Nemotron for long-form copy.
    return {
        "compressor": (groq, openrouter),
        "solver": (groq, openrouter),
        "copywriter": (openrouter, groq),
        "critic": (groq, openrouter),
        "reply_classifier": (groq, openrouter),
        "closer": (openrouter, groq),
    }


# step -> (primary, fallback) as "provider/model"
STEP_ROUTING = _routes()

JSON_STEPS = {"compressor", "solver", "critic", "reply_classifier"}

# Filled from response headers only — never from assumed defaults.
budget: dict[str, dict[str, Any]] = {
    "groq": {"headers": {}, "updated_at": None},
    "openrouter": {"headers": {}, "updated_at": None},
}


class ProviderError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _split_route(route: str) -> tuple[str, str]:
    provider, _, model = route.partition("/")
    return provider, model


def _endpoint(provider: str) -> tuple[str, str | None]:
    if provider == "groq":
        key = groq_key()
        if not key:
            raise ProviderError("GROQ_API_KEY is not set")
        return GROQ_BASE, key
    if provider == "openrouter":
        key = openrouter_key()
        if not key:
            raise ProviderError("OPENROUTER_API_KEY is not set")
        return OPENROUTER_BASE, key
    raise ProviderError(f"unknown provider {provider}")


def _headers(provider: str, key: str) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    if provider == "openrouter":
        headers["HTTP-Referer"] = "http://127.0.0.1:8787"
        headers["X-Title"] = "Scoutloop"
    return headers


def _store_rate_headers(provider: str, response: httpx.Response) -> None:
    captured: dict[str, str] = {}
    for key, value in response.headers.items():
        lower = key.lower()
        if lower.startswith("x-ratelimit-") or lower.startswith("x-ratelimit"):
            captured[lower] = value
    budget[provider] = {
        "headers": captured,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "remaining_requests": _header_int(
            captured,
            "x-ratelimit-remaining-requests",
            "x-ratelimit-remaining",
        ),
        "remaining_tokens": _header_int(
            captured,
            "x-ratelimit-remaining-tokens",
        ),
        "limit_requests": _header_int(
            captured,
            "x-ratelimit-limit-requests",
            "x-ratelimit-limit",
        ),
        "limit_tokens": _header_int(
            captured,
            "x-ratelimit-limit-tokens",
        ),
    }


def _header_int(headers: dict[str, str], *names: str) -> int | None:
    for name in names:
        raw = headers.get(name)
        if raw is None:
            continue
        # OpenRouter sometimes sends "30, 30;w=60" style values — take the first int.
        token = str(raw).split(",")[0].split(";")[0].strip()
        try:
            return int(float(token))
        except ValueError:
            continue
    return None


def budget_snapshot() -> dict[str, Any]:
    return {
        "groq": dict(budget["groq"]),
        "openrouter": dict(budget["openrouter"]),
    }


def _flatten_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or ""))
        return "".join(parts)
    return str(content)


def _extract_content(provider: str, data: Any) -> str:
    if not isinstance(data, dict):
        raise ProviderError(f"{provider} returned a non-object payload", status_code=502)
    err = data.get("error")
    if isinstance(err, dict) and (err.get("message") or err.get("code") is not None):
        code = err.get("code")
        status = code if isinstance(code, int) else 502
        raise ProviderError(f"{provider}: {err.get('message') or err}", status_code=status)
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ProviderError(
            f"{provider} returned no completion (keys={list(data)[:8]})",
            status_code=502,
        )
    choice = choices[0] if isinstance(choices[0], dict) else {}
    choice_err = choice.get("error")
    if isinstance(choice_err, dict):
        code = choice_err.get("code")
        status = code if isinstance(code, int) else 502
        raise ProviderError(
            f"{provider}: {choice_err.get('message') or choice_err}",
            status_code=status,
        )
    message = choice.get("message") if isinstance(choice.get("message"), dict) else {}
    content = _flatten_content(message.get("content"))
    if not content.strip():
        content = _flatten_content(message.get("reasoning"))
    if content.strip():
        return content
    finish = str(choice.get("finish_reason") or choice.get("native_finish_reason") or "unknown")
    raise ProviderError(f"{provider} empty completion (finish={finish})", status_code=502)


async def _complete(
    route: str,
    messages: list[dict[str, str]],
    *,
    json_mode: bool,
    temperature: float,
    max_tokens: int,
) -> dict[str, Any]:
    provider, model = _split_route(route)
    base, key = _endpoint(provider)
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    started = time.perf_counter()
    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(
            f"{base}/chat/completions",
            headers=_headers(provider, key),
            json=payload,
        )
    latency_ms = int((time.perf_counter() - started) * 1000)
    _store_rate_headers(provider, response)

    if response.status_code == 400 and json_mode:
        payload.pop("response_format", None)
        started = time.perf_counter()
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                f"{base}/chat/completions",
                headers=_headers(provider, key),
                json=payload,
            )
        latency_ms = int((time.perf_counter() - started) * 1000)
        _store_rate_headers(provider, response)

    if response.status_code == 429:
        raise ProviderError(f"{provider} rate limited", status_code=429)
    if response.status_code >= 400:
        raise ProviderError(
            f"{provider} HTTP {response.status_code}: {response.text[:400]}",
            status_code=response.status_code,
        )

    data = response.json()
    content = _extract_content(provider, data)

    return {
        "content": content,
        "provider": provider,
        "model": model,
        "latency_ms": latency_ms,
        "raw": data,
    }


def _log_call(
    *,
    lead_id: int | None,
    step: str,
    provider: str | None,
    model: str | None,
    latency_ms: int | None,
    messages: list[dict[str, str]],
    output: str,
) -> None:
    joined = "\n".join(m.get("content", "") for m in messages)
    db.insert_run_log(
        lead_id=lead_id,
        step=step,
        provider=provider,
        model=model,
        latency_ms=latency_ms,
        input_summary=truncate(joined),
        output=truncate(output, 2400),
    )


async def call_llm(
    step: str,
    messages: list[dict[str, str]],
    *,
    lead_id: int | None = None,
    temperature: float = 0.3,
    max_tokens: int = 800,
) -> dict[str, Any]:
    if step not in STEP_ROUTING:
        raise ProviderError(f"no routing configured for step '{step}'")
    primary, fallback = STEP_ROUTING[step]
    json_mode = step in JSON_STEPS

    async def run_route(route: str) -> dict[str, Any]:
        result = await _complete(
            route,
            messages,
            json_mode=json_mode,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        _log_call(
            lead_id=lead_id,
            step=step,
            provider=result["provider"],
            model=result["model"],
            latency_ms=result["latency_ms"],
            messages=messages,
            output=result["content"],
        )
        return result

    def can_failover(exc: ProviderError) -> bool:
        return (
            exc.status_code in {429, 401, 403, 502, 503}
            or exc.status_code is None
            or "is not set" in str(exc)
        )

    try:
        return await run_route(primary)
    except ProviderError as exc:
        _log_call(
            lead_id=lead_id,
            step=step,
            provider=_split_route(primary)[0],
            model=_split_route(primary)[1],
            latency_ms=None,
            messages=messages,
            output=f"PRIMARY_FAIL {exc} — {'retrying' if can_failover(exc) else 'not retrying'}",
        )
        if exc.status_code == 429:
            await asyncio.sleep(2)
            try:
                return await run_route(primary)
            except ProviderError as retry_exc:
                _log_call(
                    lead_id=lead_id,
                    step=step,
                    provider=_split_route(primary)[0],
                    model=_split_route(primary)[1],
                    latency_ms=None,
                    messages=messages,
                    output=f"PRIMARY_RETRY_FAIL {retry_exc} — trying fallback",
                )
                exc = retry_exc
        if not can_failover(exc):
            raise
        try:
            return await run_route(fallback)
        except ProviderError as fallback_exc:
            _log_call(
                lead_id=lead_id,
                step=step,
                provider=_split_route(fallback)[0],
                model=_split_route(fallback)[1],
                latency_ms=None,
                messages=messages,
                output=f"FALLBACK_FAIL {fallback_exc}",
            )
            if exc.status_code == 429:
                await asyncio.sleep(1.5)
                return await run_route(primary)
            raise fallback_exc


async def ping_provider(provider: str) -> dict[str, Any]:
    base, key = _endpoint(provider)
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(f"{base}/models", headers=_headers(provider, key))
    _store_rate_headers(provider, response)
    if response.status_code >= 400:
        raise ProviderError(
            f"{provider} HTTP {response.status_code}: {response.text[:200]}",
            status_code=response.status_code,
        )
    return budget_snapshot()[provider]

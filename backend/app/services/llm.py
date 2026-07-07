"""Unified LLM access for Werk agents.

Picks a provider in priority order:
  1. Ollama   — a local model on your own machine (no external API, no cost)
  2. Anthropic — if ANTHROPIC_API_KEY is set
  3. OpenAI    — if OPENAI_API_KEY is set
Returns (text, provider). If no provider answers, returns (None, "none") and the
caller falls back to its deterministic heuristic.
"""

from __future__ import annotations

import logging
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Fail fast if the local model server isn't running; allow long generations.
_OLLAMA_TIMEOUT = httpx.Timeout(connect=3.0, read=180.0, write=10.0, pool=10.0)


async def chat_complete(system: str, user: str, max_tokens: int = 700) -> tuple[Optional[str], str]:
    """Return (text, provider_name) from the first available provider."""
    if settings.use_ollama:
        text = await _ollama(system, user, max_tokens)
        if text:
            return text, "ollama"

    if settings.anthropic_api_key:
        text = await _anthropic(system, user, max_tokens)
        if text:
            return text, "anthropic"

    if settings.openai_api_key:
        text = await _openai(system, user, max_tokens)
        if text:
            return text, "openai"

    return None, "none"


async def _ollama(system: str, user: str, max_tokens: int) -> Optional[str]:
    """Call a local Ollama model via its native chat API."""
    url = settings.ollama_base_url.rstrip("/") + "/api/chat"
    payload = {
        "model": settings.ollama_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "options": {"num_predict": max_tokens},
    }
    try:
        async with httpx.AsyncClient(timeout=_OLLAMA_TIMEOUT) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return (data.get("message") or {}).get("content") or None
    except Exception as exc:
        logger.warning(f"Ollama call failed ({settings.ollama_base_url}): {exc}")
        return None


async def _anthropic(system: str, user: str, max_tokens: int) -> Optional[str]:
    try:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        resp = await client.messages.create(
            model="claude-3-5-sonnet-latest",
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text") or None
    except Exception as exc:
        logger.warning(f"Anthropic call failed: {exc}")
        return None


async def _openai(system: str, user: str, max_tokens: int) -> Optional[str]:
    try:
        import openai

        client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        resp = await client.chat.completions.create(
            model="gpt-4o",
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return resp.choices[0].message.content or None
    except Exception as exc:
        logger.warning(f"OpenAI call failed: {exc}")
        return None

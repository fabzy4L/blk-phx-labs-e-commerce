"""
BLK PHX LABS — LLM Client Abstraction Layer
Swap providers via LLM_PROVIDER in .env. Zero code changes required.

Supported providers:
- google (default) — Gemini 2.5 Flash, free tier, 1,500 req/day
- anthropic         — Claude Haiku 4.5, ~$0.001/inquiry with caching
- openai            — GPT-5 Mini, optional future option

Phase 1: google (free)
Phase 2+: anthropic or google paid tier depending on volume
"""

import os
from typing import Any
from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "google")


# ── RESPONSE WRAPPER ──────────────────────────────────────────────────────────

class LLMResponse:
    """Unified response object regardless of provider."""
    def __init__(self, text: str, input_tokens: int = 0, output_tokens: int = 0, provider: str = ""):
        self.text = text
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.provider = provider

    def __repr__(self):
        return f"LLMResponse(provider={self.provider}, tokens={self.input_tokens}+{self.output_tokens})"


# ── GOOGLE GEMINI ─────────────────────────────────────────────────────────────

async def _call_google(
    system_prompt: str,
    messages: list[dict],
    max_tokens: int = 1000,
) -> LLMResponse:
    """
    Call Google Gemini via AI Studio API.
    Free tier: 1,500 req/day on Flash models.
    Model: gemini-2.5-flash (free tier eligible)
    """
    import httpx

    api_key = os.getenv("GOOGLE_AI_STUDIO_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_AI_STUDIO_API_KEY not set in .env")

    model = os.getenv("GOOGLE_MODEL", "gemini-2.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    # Convert messages to Gemini format
    # Gemini uses 'user' and 'model' roles (not 'assistant')
    gemini_contents = []
    for msg in messages:
        role = "model" if msg["role"] == "assistant" else "user"
        gemini_contents.append({
            "role": role,
            "parts": [{"text": msg["content"]}]
        })

    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": gemini_contents,
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": 0.3,
        },
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

    candidate = data["candidates"][0]
    text = candidate["content"]["parts"][0]["text"]

    usage = data.get("usageMetadata", {})
    input_tokens = usage.get("promptTokenCount", 0)
    output_tokens = usage.get("candidatesTokenCount", 0)

    return LLMResponse(
        text=text,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        provider="google",
    )


# ── ANTHROPIC CLAUDE ──────────────────────────────────────────────────────────

async def _call_anthropic(
    system_prompt: str,
    messages: list[dict],
    max_tokens: int = 1000,
) -> LLMResponse:
    """
    Call Anthropic Claude API.
    Uses prompt caching on system prompt — 90% cost reduction on cached input.
    Default model: claude-haiku-4-5-20251001 (~$0.001/inquiry with caching)
    """
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    model = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

    # Enable prompt caching on system prompt — saves 90% on repeated calls
    system_with_cache = [
        {
            "type": "text",
            "text": system_prompt,
            "cache_control": {"type": "ephemeral"},
        }
    ]

    response = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_with_cache,
        messages=messages,
    )

    text = response.content[0].text
    usage = response.usage

    return LLMResponse(
        text=text,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        provider="anthropic",
    )


# ── UNIFIED ENTRYPOINT ────────────────────────────────────────────────────────

async def chat(
    system_prompt: str,
    messages: list[dict],
    max_tokens: int = 1000,
    provider: str | None = None,
) -> LLMResponse:
    """
    Unified chat call. Routes to correct provider based on LLM_PROVIDER env var.
    Override per-call with provider argument.

    Usage:
        response = await chat(system_prompt, messages)
        print(response.text)

    Switch provider in .env:
        LLM_PROVIDER=google    # free tier default
        LLM_PROVIDER=anthropic # paid, enables caching
    """
    target = provider or LLM_PROVIDER

    if target == "google":
        return await _call_google(system_prompt, messages, max_tokens)
    elif target == "anthropic":
        return await _call_anthropic(system_prompt, messages, max_tokens)
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: '{target}'. Use 'google' or 'anthropic'.")


def get_provider_info() -> dict:
    """Return current provider config — useful for dashboard display."""
    provider = LLM_PROVIDER
    if provider == "google":
        return {
            "provider": "Google Gemini",
            "model": os.getenv("GOOGLE_MODEL", "gemini-2.5-flash"),
            "tier": "free",
            "cost_per_inquiry": "$0.00",
            "daily_limit": "1,500 requests",
        }
    elif provider == "anthropic":
        return {
            "provider": "Anthropic Claude",
            "model": os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
            "tier": "paid",
            "cost_per_inquiry": "~$0.001",
            "daily_limit": "unlimited",
        }
    return {"provider": provider, "tier": "unknown"}

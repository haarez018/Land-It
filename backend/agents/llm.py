"""
Thin async wrapper around the Anthropic Claude client.

Usage:
    text = await ask(system="You are...", user="...")
    data = await ask_json(system="...", user="...")  # returns parsed dict/list

Raises NotImplementedError when ANTHROPIC_API_KEY is not set —
callers should catch this and fall back to heuristics.
"""

from __future__ import annotations

import json
import re


async def ask(
    system: str,
    user: str,
    *,
    model: str = "claude-haiku-4-5-20251001",
    max_tokens: int = 2048,
) -> str:
    """
    Send a single system+user message and return the assistant text.
    Raises NotImplementedError if ANTHROPIC_API_KEY is not configured.
    """
    from backend.dependencies import anthropic_client  # lazy import avoids circular deps
    client = anthropic_client.client  # raises NotImplementedError if no key
    message = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return message.content[0].text


async def ask_json(
    system: str,
    user: str,
    *,
    model: str = "claude-haiku-4-5-20251001",
    max_tokens: int = 2048,
) -> dict | list:
    """
    Ask Claude and parse the response as JSON.
    Strips markdown code fences if the model adds them.
    Raises json.JSONDecodeError on invalid JSON.
    """
    json_system = (
        system
        + "\n\nIMPORTANT: Respond with valid JSON only. "
          "No markdown, no code fences, no explanation — just the raw JSON value."
    )
    text = await ask(json_system, user, model=model, max_tokens=max_tokens)
    # Strip markdown code fences if present
    text = re.sub(r"^```(?:json)?\n?", "", text.strip())
    text = re.sub(r"\n?```$", "", text.strip())
    return json.loads(text.strip())

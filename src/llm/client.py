"""OpenAI-compatible chat API client (optional; no extra pip package)."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any

from src.config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL


def _extract_json_block(text: str) -> dict[str, Any]:
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fenced:
        text = fenced.group(1).strip()
    return json.loads(text)


def chat_completion_json(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.2,
) -> dict[str, Any] | None:
    if not OPENAI_API_KEY:
        return None

    payload = {
        "model": OPENAI_MODEL,
        "messages": messages,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }
    url = f"{OPENAI_BASE_URL.rstrip('/')}/chat/completions"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return None

    content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not content:
        return None
    try:
        return _extract_json_block(content)
    except json.JSONDecodeError:
        return None

"""OpenAI-compatible chat API client (DeepSeek / OpenAI / 等)."""

from __future__ import annotations

import json
import re
import ssl
import urllib.error
import urllib.request
from typing import Any

from src.config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL

_last_error: str = ""


def get_last_error() -> str:
    return _last_error


def _set_error(msg: str) -> None:
    global _last_error
    _last_error = msg


def _extract_json_block(text: str) -> dict[str, Any]:
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fenced:
        text = fenced.group(1).strip()
    return json.loads(text)


def _chat_completions_url() -> str:
    base = OPENAI_BASE_URL.rstrip("/")
    if base.endswith("/v1"):
        return f"{base}/chat/completions"
    return f"{base}/chat/completions"


def _request_completion(
    messages: list[dict[str, str]],
    *,
    temperature: float,
    json_mode: bool,
) -> str | None:
    payload: dict[str, Any] = {
        "model": OPENAI_MODEL,
        "messages": messages,
        "temperature": temperature,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    url = _chat_completions_url()
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
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=90, context=ctx) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        _set_error(f"HTTP {exc.code} @ {url}\n{detail[:800]}")
        if json_mode and exc.code in (400, 422):
            return None
        return None
    except urllib.error.URLError as exc:
        _set_error(f"网络错误 @ {url}: {exc.reason}")
        return None
    except (json.JSONDecodeError, TimeoutError) as exc:
        _set_error(f"响应解析/超时: {exc}")
        return None

    _set_error("")
    return body.get("choices", [{}])[0].get("message", {}).get("content", "") or None


def chat_completion_json(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.2,
) -> dict[str, Any] | None:
    if not OPENAI_API_KEY:
        _set_error("未配置 OPENAI_API_KEY")
        return None

    content = _request_completion(messages, temperature=temperature, json_mode=True)
    if content is None and get_last_error().startswith("HTTP 4"):
        # json_mode 被拒时已在第一次请求里记下错误；再试普通模式
        pass
    if content is None:
        content = _request_completion(messages, temperature=temperature, json_mode=False)
    if not content:
        return None

    try:
        return _extract_json_block(content)
    except json.JSONDecodeError:
        _set_error(f"模型返回非 JSON: {content[:300]}")
        return None

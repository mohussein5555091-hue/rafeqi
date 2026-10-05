"""The model client. The app only needs one call: a system prompt and a user message in, text and token counts out.

`AnthropicClient` calls the Claude Messages API over https (only when AI is turned on and a key is set). Tests use a
fake client with the same `complete()`; nothing in the test suite ever calls the real API.
"""

import time
from dataclasses import dataclass
from typing import Protocol

import httpx

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"


@dataclass(frozen=True)
class Completion:
    text: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int


class LlmClient(Protocol):
    def complete(self, *, model: str, system: str, user: str, max_tokens: int) -> Completion: ...


class LlmError(RuntimeError):
    pass


class AnthropicClient:
    def __init__(self, api_key: str, timeout_s: float = 60.0):
        self._key, self._timeout = api_key, timeout_s

    def complete(self, *, model: str, system: str, user: str, max_tokens: int) -> Completion:
        started = time.monotonic()
        try:
            r = httpx.post(API_URL, timeout=self._timeout, headers={
                "x-api-key": self._key, "anthropic-version": API_VERSION, "content-type": "application/json",
            }, json={"model": model, "max_tokens": max_tokens, "system": system, "messages": [{"role": "user", "content": user}]})
        except httpx.HTTPError as e:
            raise LlmError(f"network: {type(e).__name__}") from e
        if r.status_code != 200:
            raise LlmError(f"http {r.status_code}")
        body = r.json()
        text = "".join(b.get("text", "") for b in body.get("content", []) if b.get("type") == "text")
        usage = body.get("usage") or {}
        return Completion(text, int(usage.get("input_tokens", 0)), int(usage.get("output_tokens", 0)),
                          int((time.monotonic() - started) * 1000))

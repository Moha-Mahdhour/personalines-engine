"""Chat-completion client with bounded, jittered retries.

Uses urllib from the standard library, so no HTTP dependency is needed.
The transport and sleep functions are injectable, which is how the retry
policy is tested without a network.
"""
from __future__ import annotations

import json
import random
import time
import urllib.error
import urllib.request
from typing import Callable, Protocol, Sequence

Message = dict[str, str]
# (url, headers, body, timeout) -> (status_code, response_body)
Transport = Callable[[str, dict[str, str], bytes, float], tuple[int, bytes]]

RETRYABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}


class LLMError(RuntimeError):
    """The request failed permanently or exhausted its retries."""


class ChatClient(Protocol):
    def complete(self, messages: Sequence[Message]) -> str: ...


def urllib_transport(url: str, headers: dict[str, str], body: bytes, timeout: float) -> tuple[int, bytes]:
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


class OpenAIChatClient:
    url = "https://api.openai.com/v1/chat/completions"

    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo", *, temperature: float = 1.0,
                 timeout: float = 20.0, max_retries: int = 5, base_delay: float = 1.0, max_delay: float = 30.0,
                 transport: Transport = urllib_transport, sleep: Callable[[float], None] = time.sleep,
                 rng: Callable[[], float] = random.random) -> None:
        if not api_key:
            raise LLMError("OPENAI_API_KEY is not set")
        self.model, self.temperature, self.timeout = model, temperature, timeout
        self.max_retries, self.base_delay, self.max_delay = max_retries, base_delay, max_delay
        self._headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
        self._transport, self._sleep, self._rng = transport, sleep, rng

    def _backoff(self, attempt: int) -> float:
        return min(self.max_delay, self.base_delay * (2 ** attempt)) + self._rng() * self.base_delay

    def complete(self, messages: Sequence[Message]) -> str:
        body = json.dumps({"model": self.model, "temperature": self.temperature,
                           "messages": list(messages)}).encode("utf-8")
        last_error = "no attempts made"
        for attempt in range(self.max_retries + 1):
            try:
                status, raw = self._transport(self.url, self._headers, body, self.timeout)
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
                status, raw, last_error = None, b"", f"network error: {exc}"
            else:
                if status == 200:
                    try:
                        return json.loads(raw)["choices"][0]["message"]["content"]
                    except (ValueError, KeyError, IndexError, TypeError):
                        last_error = "malformed response body"
                else:
                    last_error = f"HTTP {status}: {raw[:200].decode('utf-8', 'replace')}"
                    if status not in RETRYABLE_STATUS:
                        raise LLMError(last_error)          # bad key, bad request: retrying won't help
            if attempt < self.max_retries:
                self._sleep(self._backoff(attempt))
        raise LLMError(f"gave up after {self.max_retries + 1} attempts ({last_error})")

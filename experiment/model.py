"""OpenAI-compatible chat model client with token and latency measurements."""

from __future__ import annotations

import json
import time
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass
class Generation:
    text: str
    input_tokens: int
    output_tokens: int
    latency_seconds: float


class Model:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    def generate(self, messages: list[dict[str, str]], seed: int) -> Generation:
        body = {
            "model": self.config["name"], "messages": messages,
            "temperature": self.config.get("temperature", 0),
            "max_tokens": self.config.get("max_tokens", 2048), "seed": seed,
        }
        request = urllib.request.Request(
            self.config.get("base_url", "http://127.0.0.1:8000/v1") + "/chat/completions",
            data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json"},
        )
        started = time.monotonic()
        with urllib.request.urlopen(request, timeout=self.config.get("request_timeout_seconds", 1800)) as response:
            payload = json.load(response)
        usage = payload.get("usage", {})
        return Generation(
            payload["choices"][0]["message"]["content"],
            int(usage.get("prompt_tokens", 0)), int(usage.get("completion_tokens", 0)),
            time.monotonic() - started,
        )


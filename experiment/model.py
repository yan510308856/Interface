"""OpenAI-compatible chat model client with token and latency measurements."""

from __future__ import annotations

import json
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Generation:
    text: str
    input_tokens: int
    output_tokens: int
    latency_seconds: float
    tool_calls: list[dict[str, Any]] = field(default_factory=list)


class Model:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    def generate(
        self,
        messages: list[dict[str, Any]],
        seed: int,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
    ) -> Generation:
        body = {
            "model": self.config["name"], "messages": messages,
            "temperature": self.config.get("temperature", 0),
            "max_tokens": self.config.get("max_tokens", 2048), "seed": seed,
        }
        if tools is not None:
            body["tools"] = tools
            body["tool_choice"] = tool_choice
        request = urllib.request.Request(
            self.config.get("base_url", "http://127.0.0.1:8000/v1") + "/chat/completions",
            data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json"},
        )
        started = time.monotonic()
        with urllib.request.urlopen(request, timeout=self.config.get("request_timeout_seconds", 1800)) as response:
            payload = json.load(response)
        usage = payload.get("usage", {})
        message = payload["choices"][0]["message"]
        return Generation(
            message.get("content") or "",
            int(usage.get("prompt_tokens", 0)), int(usage.get("completion_tokens", 0)),
            time.monotonic() - started,
            message.get("tool_calls") or [],
        )

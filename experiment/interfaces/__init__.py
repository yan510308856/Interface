"""Values shared by the two action parsers, not execution capabilities."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ActionResult:
    status: str
    observation: str
    responses: list[dict[str, Any]] = field(default_factory=list)
    unsafe_attempt: bool = False

    @property
    def finished(self) -> bool:
        return self.status == "finish"


def observation(responses: list[dict[str, Any]]) -> str:
    return json.dumps(responses, ensure_ascii=False)

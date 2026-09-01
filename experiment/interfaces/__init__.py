"""Shared result contract for the two R5 action interfaces."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any


OBSERVATION_CHARACTER_LIMIT = 8192


def unwrap_single_code_fence(source: Any, allowed_languages: set[str]) -> Any:
    """Remove one whole-output Markdown fence without changing its payload."""
    if not isinstance(source, str):
        return source
    stripped = source.strip()
    lines = stripped.splitlines()
    if len(lines) < 3 or lines[-1].strip() != "```":
        return source
    opening = lines[0].strip()
    if not opening.startswith("```"):
        return source
    language = opening[3:].strip().lower()
    if language not in allowed_languages:
        return source
    payload = "\n".join(lines[1:-1])
    if "```" in payload:
        return source
    return payload


def format_observation(responses: list[dict[str, Any]]) -> str:
    """Return a deterministic JSON observation with an exact character bound."""
    raw = json.dumps(responses, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    common = {
        "response_count": len(responses),
        "responses_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
    }
    payload = {**common, "responses": responses, "text_prefix": None, "truncated": False}
    rendered = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if len(rendered) <= OBSERVATION_CHARACTER_LIMIT:
        return rendered

    prefix = raw[: OBSERVATION_CHARACTER_LIMIT - 256]
    payload = {**common, "responses": [], "text_prefix": prefix, "truncated": True}
    rendered = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    while len(rendered) > OBSERVATION_CHARACTER_LIMIT:
        excess = len(rendered) - OBSERVATION_CHARACTER_LIMIT
        prefix = prefix[: -max(excess, 1)]
        payload["text_prefix"] = prefix
        rendered = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return rendered


@dataclass(frozen=True)
class ActionResult:
    """One deterministic, serializable adapter result."""

    action_id: str
    parse_status: str
    backend_op_ids: list[str] = field(default_factory=list)
    observation: str = ""
    error: dict[str, Any] | None = None
    duration_ms: float = 0.0
    backend_responses: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

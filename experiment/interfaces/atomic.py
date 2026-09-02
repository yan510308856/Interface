"""Atomic interface: one model action performs at most one backend operation."""

from __future__ import annotations

import json

from experiment.backend import Backend, OPERATIONS
from experiment.interfaces import ActionResult, observation


def execute_action(source: str, backend: Backend, action_id: str) -> ActionResult:
    unsafe_attempt = False
    try:
        action = json.loads(source)
        if not isinstance(action, dict):
            raise ValueError("action must be a JSON object")
        if action.get("type") == "finish":
            if set(action) - {"type", "message"} or not isinstance(action.get("message", ""), str):
                raise ValueError("invalid finish action")
            return ActionResult("finish", observation([{"message": action.get("message", "")}]))
        if set(action) != {"type", "operation", "arguments"} or action["type"] != "tool_call":
            raise ValueError("expected a tool_call or finish action")
        if action["operation"] not in OPERATIONS:
            unsafe_attempt = True
            raise ValueError("operation is not available")
        if not isinstance(action["arguments"], dict):
            raise ValueError("arguments must be an object")
        response = backend.execute(action["operation"], action["arguments"], action_id)
        return ActionResult("ok", observation([response]), [response])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        return ActionResult("invalid", observation([{"error": str(exc)}]), unsafe_attempt=unsafe_attempt)

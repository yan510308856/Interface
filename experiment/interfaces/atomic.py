"""Atomic JSON action adapter: one valid tool call, one backend attempt."""

from __future__ import annotations

import json
import time
from experiment import backend
from experiment.interfaces import ActionResult, format_observation


def _invalid(action_id: str, started: float, message: str) -> ActionResult:
    error = {"code": "invalid_action", "message": message, "retryable": False}
    return ActionResult(
        action_id=action_id,
        parse_status="invalid",
        observation=format_observation([{"ok": False, "error": error}]),
        error=error,
        duration_ms=round((time.monotonic() - started) * 1000, 3),
    )


def execute_action(source: str, context: backend.BackendContext, action_id: str) -> ActionResult:
    """Parse and execute one Atomic action without performing adapter-side I/O."""
    started = time.monotonic()
    try:
        action = json.loads(source)
    except (json.JSONDecodeError, TypeError) as exc:
        return _invalid(action_id, started, f"action must be one JSON object: {exc}")
    if not isinstance(action, dict):
        return _invalid(action_id, started, "action must be a JSON object")

    action_type = action.get("type")
    if action_type == "finish":
        if set(action) - {"type", "message"} or not isinstance(action.get("message", ""), str):
            return _invalid(action_id, started, "invalid finish action")
        observation = format_observation([{"ok": True, "type": "finish", "message": action.get("message", "")}])
        return ActionResult(
            action_id=action_id,
            parse_status="finish",
            observation=observation,
            duration_ms=round((time.monotonic() - started) * 1000, 3),
        )

    if action_type != "tool_call":
        return _invalid(action_id, started, "type must be the literal string 'tool_call' or 'finish'")
    if set(action) != {"type", "operation", "arguments"}:
        return _invalid(action_id, started, "tool_call requires only type, operation, and arguments")
    if not isinstance(action["operation"], str) or not isinstance(action["arguments"], dict):
        return _invalid(action_id, started, "operation must be a string and arguments must be an object")
    if action["operation"] not in backend.load_schema()["operations"]:
        return _invalid(action_id, started, "operation is not in the canonical schema")

    context.action_id = action_id
    request = {
        "operation": action["operation"],
        "arguments": action["arguments"],
        "request_id": f"{action_id}:op1",
    }
    response = backend.execute(request, context)
    error = None if response["ok"] else response["error"]
    return ActionResult(
        action_id=action_id,
        parse_status="ok",
        backend_op_ids=[response["request_id"]],
        observation=format_observation([response]),
        error=error,
        duration_ms=round((time.monotonic() - started) * 1000, 3),
        backend_responses=[response],
    )

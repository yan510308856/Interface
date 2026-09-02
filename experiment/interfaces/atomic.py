"""Atomic interface: one model action performs at most one backend operation."""

from __future__ import annotations

import json

from experiment.backend import Backend, OPERATIONS
from experiment.interfaces import ActionResult, observation


def _extract_json_object(source: str) -> str:
    objects = []
    start = None
    depth = 0
    in_string = escaped = False
    for index, character in enumerate(source):
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
        elif character == '"' and depth:
            in_string = True
        elif character == "{":
            if depth == 0:
                start = index
            depth += 1
        elif character == "}" and depth:
            depth -= 1
            if depth == 0:
                candidate = source[start:index + 1]
                try:
                    if isinstance(json.loads(candidate), dict):
                        objects.append(candidate)
                except json.JSONDecodeError:
                    pass
    if len(objects) != 1:
        raise ValueError("expected exactly one complete JSON object")
    return objects[0]


def execute_action(source: str, backend: Backend, action_id: str) -> ActionResult:
    unsafe_attempt = False
    try:
        action = json.loads(_extract_json_object(source))
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

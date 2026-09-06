"""Unified static action interface for execution-granularity experiments."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from experiment.backend import (
    OPERATION_ORDER,
    Backend,
    OPERATIONS,
    operation_argument_error,
    operation_argument_schema,
)
from experiment.interfaces import ActionResult


ACTION_TOOL_NAME = "submit_action"
GRANULARITY_LEVELS = {1, 2, 4}


def build_tools(max_ops_per_action: int) -> list[dict[str, Any]]:
    """Build the same action schema with only its capacity bound parameterized."""
    validate_capacity(max_ops_per_action)
    operation_variants = [{
        "type": "object",
        "properties": {
            "name": {"type": "string", "enum": [name]},
            "arguments": operation_argument_schema(name),
        },
        "required": ["name", "arguments"],
        "additionalProperties": False,
    } for name in OPERATION_ORDER]
    return [{
        "type": "function",
        "function": {
            "name": ACTION_TOOL_NAME,
            "description": (
                "Submit one ordered action. Include one or more precommitted "
                "backend operations, or submit finish=\"done\" with no operations."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "operations": {
                        "type": "array",
                        "maxItems": max_ops_per_action,
                        "items": {"oneOf": operation_variants},
                    },
                    "finish": {"type": "string"},
                },
                "required": ["operations"],
                "additionalProperties": False,
            },
        },
    }]


def validate_capacity(max_ops_per_action: int) -> None:
    if not isinstance(max_ops_per_action, int) or isinstance(max_ops_per_action, bool):
        raise ValueError("max_ops_per_action must be an integer")
    if max_ops_per_action < 1:
        raise ValueError("max_ops_per_action must be at least 1")


def _observation(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _invalid(
    reason: str,
    *,
    unsafe_attempt: bool = False,
    requested_operations: list[dict[str, Any]] | None = None,
    parent_tool_call_id: str | None = None,
) -> ActionResult:
    return ActionResult(
        "invalid",
        _observation({
            "status": "invalid",
            "error_type": "action_validation_error",
            "reason": reason,
            "backend_operations_executed": 0,
        }),
        unsafe_attempt=unsafe_attempt,
        requested_operations=requested_operations or [],
        parent_tool_call_id=parent_tool_call_id,
    )


def _tool_call_id(tool_calls: list[dict[str, Any]]) -> str | None:
    if len(tool_calls) != 1 or not isinstance(tool_calls[0], dict):
        return None
    call_id = tool_calls[0].get("id")
    return call_id if isinstance(call_id, str) else None


def _batch_item(
    index: int,
    operation: dict[str, Any],
    response: dict[str, Any],
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "index": index,
        "name": operation["name"],
        "arguments": operation["arguments"],
        "operation_id": response.get("operation_id"),
        "ok": response.get("ok", False),
        "status": response.get("status", "error"),
    }
    for key in ("result", "error"):
        if key in response:
            item[key] = response[key]
    return item


@dataclass
class GranularityActionAdapter:
    """Validate and execute one static action through the canonical Backend."""

    max_ops_per_action: int

    def __post_init__(self) -> None:
        validate_capacity(self.max_ops_per_action)

    def _parse(
        self,
        tool_calls: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], bool, str | None, bool]:
        if not isinstance(tool_calls, list) or len(tool_calls) != 1:
            raise ValueError("expected exactly one submit_action tool call")
        tool_call = tool_calls[0]
        if not isinstance(tool_call, dict) or tool_call.get("type") != "function":
            raise ValueError("expected a function tool call")
        function = tool_call.get("function")
        if not isinstance(function, dict) or function.get("name") != ACTION_TOOL_NAME:
            raise ValueError("expected the submit_action tool")
        raw_arguments = function.get("arguments")
        if not isinstance(raw_arguments, str):
            raise ValueError("arguments must be JSON text")
        arguments = json.loads(raw_arguments)
        if not isinstance(arguments, dict):
            raise ValueError("arguments must be an object")
        if set(arguments) - {"operations", "finish"}:
            raise ValueError("action arguments may contain only operations and finish")
        operations = arguments.get("operations")
        if not isinstance(operations, list):
            raise ValueError("operations must be a list")
        finish = arguments.get("finish")
        if finish is not None and not isinstance(finish, str):
            raise ValueError("finish must be a string when provided")
        if finish is not None:
            if finish != "done":
                raise ValueError('completion must be exactly finish="done"')
            if operations:
                raise ValueError("finish cannot be combined with backend operations")
            return [], True, _tool_call_id(tool_calls), False
        if not operations:
            raise ValueError("a non-terminal action must contain at least one operation")
        if len(operations) > self.max_ops_per_action:
            raise ValueError(
                f"action contains {len(operations)} operations; "
                f"maximum is {self.max_ops_per_action}"
            )
        unsafe_attempt = False
        normalized: list[dict[str, Any]] = []
        for index, operation in enumerate(operations, 1):
            if not isinstance(operation, dict) or set(operation) != {"name", "arguments"}:
                raise ValueError(f"operation {index} must contain only name and arguments")
            name = operation["name"]
            arguments = operation["arguments"]
            if not isinstance(name, str) or name not in OPERATIONS:
                unsafe_attempt = True
                raise ValueError(f"operation {index} is not an available backend operation")
            if not isinstance(arguments, dict):
                raise ValueError(f"arguments for operation {index} must be an object")
            argument_error = operation_argument_error(index, name, arguments)
            if argument_error:
                raise ValueError(argument_error)
            normalized.append({"name": name, "arguments": arguments})
        return normalized, False, _tool_call_id(tool_calls), unsafe_attempt

    def execute_action(
        self,
        tool_calls: list[dict[str, Any]],
        backend: Backend,
        action_id: str,
    ) -> ActionResult:
        try:
            operations, finished, parent_tool_call_id, unsafe_attempt = self._parse(tool_calls)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            requested_operations: list[dict[str, Any]] = []
            try:
                raw = tool_calls[0]["function"]["arguments"]
                payload = json.loads(raw)
                if isinstance(payload, dict) and isinstance(payload.get("operations"), list):
                    requested_operations = [
                        item for item in payload["operations"]
                        if isinstance(item, dict) and "name" in item and "arguments" in item
                    ]
            except (IndexError, KeyError, TypeError, json.JSONDecodeError):
                pass
            return _invalid(
                str(exc),
                unsafe_attempt="not an available backend operation" in str(exc),
                requested_operations=requested_operations,
                parent_tool_call_id=_tool_call_id(tool_calls),
            )

        if finished:
            return ActionResult(
                "finish",
                _observation({"status": "finish", "operations": []}),
                parent_tool_call_id=parent_tool_call_id,
            )

        responses: list[dict[str, Any]] = []
        for index, operation in enumerate(operations, 1):
            response = backend.execute(
                operation["name"], operation["arguments"], action_id,
                operation_index=index,
                parent_tool_call_id=parent_tool_call_id,
            )
            responses.append(_batch_item(index, operation, response))
        return ActionResult(
            "ok",
            _observation({"status": "ok", "operations": responses}),
            responses,
            unsafe_attempt=unsafe_attempt,
            requested_operations=operations,
            parent_tool_call_id=parent_tool_call_id,
        )

"""Atomic interface: one model action performs at most one backend operation."""

from __future__ import annotations

import json
from typing import Any

from experiment.backend import Backend, OPERATIONS
from experiment.interfaces import ActionResult, observation


def _tool(
    name: str,
    description: str,
    properties: dict[str, Any],
    required: list[str] | None = None,
) -> dict[str, Any]:
    parameters: dict[str, Any] = {
        "type": "object", "properties": properties, "additionalProperties": False,
    }
    if required:
        parameters["required"] = required
    return {
        "type": "function",
        "function": {"name": name, "description": description, "parameters": parameters},
    }


ATOMIC_TOOLS = [
    _tool("read_file", "Read UTF-8 text from a repository file. Defaults to start_line=1 and at most 400 lines when end_line is omitted.", {
        "path": {"type": "string"},
        "start_line": {"type": "integer"},
        "end_line": {"type": "integer"},
    }, ["path"]),
    _tool("search_text", "Search repository text. Defaults to path='.', glob=None, and case_sensitive=False; .git is excluded.", {
        "query": {"type": "string"},
        "path": {"type": "string"},
        "glob": {"type": "string"},
        "case_sensitive": {"type": "boolean"},
    }, ["query"]),
    _tool("replace_text", "Replace exact text in a repository file. expected_replacements defaults to 1 and must match.", {
        "path": {"type": "string"},
        "old_text": {"type": "string"},
        "new_text": {"type": "string"},
        "expected_replacements": {"type": "integer"},
    }, ["path", "old_text", "new_text"]),
    _tool("create_file", "Create one new repository file; existing files are not overwritten.", {
        "path": {"type": "string"},
        "content": {"type": "string"},
    }, ["path", "content"]),
    _tool("delete_file", "Delete one repository file after the shared permission check.", {
        "path": {"type": "string"},
    }, ["path"]),
    _tool("run_process", "Run one argv through the shared process allowlist. timeout_seconds defaults to 300.", {
        "argv": {"type": "array", "items": {"type": "string"}},
        "timeout_seconds": {"type": "integer"},
    }, ["argv"]),
    _tool("git_diff", "Read the repository diff. Defaults to path='.' and staged=False.", {
        "path": {"type": "string"},
        "staged": {"type": "boolean"},
    }),
    _tool("finish", "End only after the repository task is complete; finish does not call the Backend.", {"message": {"type": "string"}}),
]


def execute_action(tool_calls: list[dict[str, Any]], backend: Backend, action_id: str) -> ActionResult:
    unsafe_attempt = False
    try:
        if not isinstance(tool_calls, list) or len(tool_calls) != 1:
            raise ValueError("expected exactly one tool call")
        function = tool_calls[0]["function"]
        name = function["name"]
        arguments = json.loads(function["arguments"])
        if not isinstance(arguments, dict):
            raise ValueError("arguments must be an object")
        if name == "finish":
            if set(arguments) - {"message"} or not isinstance(arguments.get("message", ""), str):
                raise ValueError("invalid finish arguments")
            return ActionResult("finish", observation([{"message": arguments.get("message", "")}]))
        if name not in OPERATIONS:
            unsafe_attempt = True
            raise ValueError("operation is not available")
        response = backend.execute(name, arguments, action_id)
        return ActionResult("ok", observation([response]), [response])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        return ActionResult("invalid", observation([{"error": str(exc)}]), unsafe_attempt=unsafe_attempt)

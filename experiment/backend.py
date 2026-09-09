"""The only filesystem, process, and Git implementation used by either interface."""

from __future__ import annotations

import fnmatch
import json
import os
import subprocess
import time
from collections import defaultdict
from copy import deepcopy
from pathlib import Path, PurePosixPath
from typing import Any

from experiment.logging import JsonlLogger
from experiment.permission import PermissionEngine


OPERATION_ARGUMENT_SCHEMAS: dict[str, dict[str, Any]] = {
    "read_file": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Repository-relative file path."},
            "start_line": {"type": "integer", "description": "1-based first line; defaults to 1."},
            "end_line": {"type": "integer", "description": "Inclusive last line; defaults to the read limit."},
        },
        "required": ["path"],
        "additionalProperties": False,
    },
    "list_files": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Repository-relative file or directory; defaults to .",
                "default": ".",
            },
            "glob": {
                "type": "string",
                "description": "Optional glob matched against normalized repository-relative file paths.",
            },
            "recursive": {
                "type": "boolean",
                "description": "Recurse into subdirectories; defaults to true.",
                "default": True,
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of paths to return; defaults to 200.",
                "minimum": 1,
                "maximum": 1000,
                "default": 200,
            },
        },
        "additionalProperties": False,
    },
    "search_text": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Text to search for."},
            "path": {"type": "string", "description": "Repository-relative file or directory; defaults to ."},
            "glob": {"type": "string", "description": "Optional repository-relative glob filter."},
            "case_sensitive": {"type": "boolean", "description": "Whether matching is case-sensitive; defaults to false."},
        },
        "required": ["query"],
        "additionalProperties": False,
    },
    "replace_text": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Repository-relative file path."},
            "old_text": {"type": "string", "description": "Exact text to replace."},
            "new_text": {"type": "string", "description": "Replacement text."},
            "expected_replacements": {"type": "integer", "description": "Expected match count; defaults to 1."},
        },
        "required": ["path", "old_text", "new_text"],
        "additionalProperties": False,
    },
    "create_file": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Repository-relative new file path."},
            "content": {"type": "string", "description": "UTF-8 file content."},
        },
        "required": ["path", "content"],
        "additionalProperties": False,
    },
    "delete_file": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Repository-relative file path."},
        },
        "required": ["path"],
        "additionalProperties": False,
    },
    "run_process": {
        "type": "object",
        "properties": {
            "argv": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Argument vector; no shell string. The current policy permits only "
                    "argv prefixes [\"python\", \"-m\", \"pytest\"], "
                    "[\"python3\", \"-m\", \"pytest\"], or [\"pytest\"]; "
                    "shell=False."
                ),
            },
            "timeout_seconds": {"type": "integer", "description": "Process timeout; defaults to 300 seconds."},
        },
        "required": ["argv"],
        "additionalProperties": False,
    },
    "git_diff": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Repository-relative path; defaults to ."},
            "staged": {"type": "boolean", "description": "Read staged diff when true; defaults to false."},
        },
        "additionalProperties": False,
    },
}

OPERATION_ORDER = tuple(OPERATION_ARGUMENT_SCHEMAS)
OPERATIONS = set(OPERATION_ORDER)
ARGUMENT_ORDER = {
    name: tuple(schema["properties"])
    for name, schema in OPERATION_ARGUMENT_SCHEMAS.items()
}
REQUIRED_ARGUMENTS = {
    name: set(schema.get("required", ()))
    for name, schema in OPERATION_ARGUMENT_SCHEMAS.items()
}
OPERATION_DESCRIPTIONS = {
    "read_file": "Read UTF-8 text from a repository file. Defaults to start_line=1 and at most 400 lines when end_line is omitted.",
    "list_files": "List repository-relative files, excluding .git and symlinks. Defaults to path='.', recursive=True, and max_results=200; results are sorted and truncation is reported.",
    "search_text": "Search repository text. Defaults to path='.', glob=None, and case_sensitive=False; .git is excluded.",
    "replace_text": "Replace exact text in a repository file. expected_replacements defaults to 1 and must match.",
    "create_file": "Create one new repository file; existing files are not overwritten.",
    "delete_file": "Delete one repository file after the shared permission check.",
    "run_process": (
        "Run one argv through the shared process allowlist. The current policy permits "
        "only argv prefixes [\"python\", \"-m\", \"pytest\"], "
        "[\"python3\", \"-m\", \"pytest\"], or [\"pytest\"]; shell=False. "
        "timeout_seconds defaults to 300."
    ),
    "git_diff": "Read the repository diff. Defaults to path='.' and staged=False.",
}


def operation_argument_schema(operation: str) -> dict[str, Any]:
    """Return a copy of the canonical JSON schema for one Backend operation."""
    return deepcopy(OPERATION_ARGUMENT_SCHEMAS[operation])


def operation_tool_schema(operation: str) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": operation,
            "description": OPERATION_DESCRIPTIONS[operation],
            "parameters": operation_argument_schema(operation),
        },
    }


def _matches_json_type(value: Any, schema: dict[str, Any]) -> bool:
    schema_type = schema.get("type")
    if schema_type == "string":
        return isinstance(value, str)
    if schema_type == "integer":
        return (
            isinstance(value, int)
            and not isinstance(value, bool)
            and value >= schema.get("minimum", value)
            and value <= schema.get("maximum", value)
        )
    if schema_type == "boolean":
        return isinstance(value, bool)
    if schema_type == "array":
        return isinstance(value, list) and all(
            _matches_json_type(item, schema.get("items", {})) for item in value
        )
    if schema_type == "object":
        return isinstance(value, dict)
    return True


def operation_argument_error(index: int, operation: str, arguments: Any) -> str | None:
    """Validate model-facing operation arguments without executing the Backend."""
    schema = OPERATION_ARGUMENT_SCHEMAS[operation]
    prefix = f"operation {index} ({operation})"
    if not isinstance(arguments, dict):
        return f"{prefix}: arguments must be an object"
    allowed = list(schema["properties"])
    required = list(schema.get("required", ()))
    format_fields = lambda fields: json.dumps(fields, ensure_ascii=False)
    unknown = sorted(set(arguments) - set(allowed))
    if unknown:
        return f"{prefix}: unsupported arguments {format_fields(unknown)}; allowed arguments {format_fields(allowed)}; required arguments {format_fields(required)}"
    missing = sorted(set(required) - set(arguments))
    if missing:
        return f"{prefix}: missing arguments {format_fields(missing)}; allowed arguments {format_fields(allowed)}; required arguments {format_fields(required)}"
    for name, value in arguments.items():
        if not _matches_json_type(value, schema["properties"][name]):
            expected = schema["properties"][name].get("type", "valid JSON value")
            return f"{prefix}: argument {name!r} must have type {expected}; allowed arguments {format_fields(allowed)}; required arguments {format_fields(required)}"
    return None

DEFAULT_READ_LINES = 400
DEFAULT_LIST_FILES_RESULTS = 200
MAX_LIST_FILES_RESULTS = 1000


class Backend:
    def __init__(self, repo_root: Path, permission: PermissionEngine, logger: JsonlLogger, max_operations: int) -> None:
        self.repo_root = repo_root.resolve()
        self.permission = permission
        self.logger = logger
        self.max_operations = max_operations
        self.operation_count = 0
        self._action_operation_counts: dict[str, int] = defaultdict(int)

    def execute(
        self,
        operation: str,
        arguments: dict[str, Any],
        action_id: str,
        *,
        operation_index: int | None = None,
        parent_tool_call_id: str | None = None,
    ) -> dict[str, Any]:
        started = time.monotonic()
        action_id = str(action_id)
        if operation_index is None:
            self._action_operation_counts[action_id] += 1
            operation_index = self._action_operation_counts[action_id]
        else:
            self._action_operation_counts[action_id] = max(
                self._action_operation_counts[action_id], operation_index,
            )
        operation_id = f"{action_id}.{operation_index}"
        self.operation_count += 1
        status = "error"
        result: Any = None
        error: str | None = None
        try:
            if self.operation_count > self.max_operations:
                raise RuntimeError("operation budget exhausted")
            if operation not in OPERATIONS:
                raise ValueError(f"unknown operation: {operation}")
            allowed, reason = self.permission.check(operation, arguments)
            if not allowed:
                status = "denied"
                raise PermissionError(reason)
            result = getattr(self, f"_{operation}")(**arguments)
            status = "success"
        except (OSError, UnicodeError, ValueError, RuntimeError, PermissionError, TypeError, subprocess.SubprocessError) as exc:
            error = str(exc)
        response = {
            "ok": status == "success",
            "operation": operation,
            "operation_id": operation_id,
            "operation_index": operation_index,
            "status": status,
        }
        if result is not None:
            response["result"] = result
        if error is not None:
            response["error"] = error
        self.logger.append({
            "event": "backend_operation", "action_id": action_id,
            "operation_id": operation_id, "operation_index": operation_index,
            "parent_tool_call_id": parent_tool_call_id,
            "operation": operation,
            "arguments": arguments, "status": status, "result": result, "error": error,
            "duration_ms": round((time.monotonic() - started) * 1000, 3),
        })
        return response

    def _file(self, path: str, *, allow_root: bool = False) -> tuple[Path, str]:
        return self.permission.resolve_path(path, allow_root=allow_root)

    def _read_file(self, path: str, start_line: int = 1, end_line: int | None = None) -> dict[str, Any]:
        file_path, relative = self._file(path)
        if start_line < 1 or (end_line is not None and end_line < start_line):
            raise ValueError("invalid line range")
        lines = file_path.read_text(encoding="utf-8").splitlines(keepends=True)
        total_lines = len(lines)
        truncated = end_line is None and start_line + DEFAULT_READ_LINES - 1 < total_lines
        effective_end = end_line if end_line is not None else start_line + DEFAULT_READ_LINES - 1
        returned_end = min(effective_end, total_lines)
        return {
            "path": relative,
            "content": "".join(lines[start_line - 1 : effective_end]),
            "start_line": start_line,
            "end_line": returned_end,
            "total_lines": total_lines,
            "truncated": truncated,
        }

    def _list_files(
        self,
        path: str = ".",
        glob: str | None = None,
        recursive: bool = True,
        max_results: int = DEFAULT_LIST_FILES_RESULTS,
    ) -> dict[str, Any]:
        if not isinstance(max_results, int) or isinstance(max_results, bool):
            raise ValueError("max_results must be an integer")
        if not 1 <= max_results <= MAX_LIST_FILES_RESULTS:
            raise ValueError(f"max_results must be between 1 and {MAX_LIST_FILES_RESULTS}")
        root, relative_root = self._file(path, allow_root=True)
        if root.is_symlink():
            raise ValueError("symlink paths are not listable")
        if not root.exists():
            raise FileNotFoundError(path)
        if root.is_file():
            candidates = [root]
        elif root.is_dir():
            candidates: list[Path] = []
            pending = [root]
            while pending:
                directory = pending.pop()
                for candidate in directory.iterdir():
                    if candidate.is_symlink():
                        continue
                    if candidate.is_file():
                        candidates.append(candidate)
                    elif recursive and candidate.is_dir():
                        pending.append(candidate)
        else:
            raise ValueError("path must be a file or directory")

        paths = []
        for candidate in candidates:
            relative = candidate.relative_to(self.repo_root).as_posix()
            if ".git" in Path(relative).parts:
                continue
            if glob is not None and not PurePosixPath(relative).match(glob):
                continue
            paths.append(relative)
        paths.sort()
        return {
            "path": relative_root,
            "glob": glob,
            "recursive": recursive,
            "max_results": max_results,
            "paths": paths[:max_results],
            "returned": min(len(paths), max_results),
            "total_matches": len(paths),
            "truncated": len(paths) > max_results,
        }

    def _search_text(self, query: str, path: str = ".", glob: str | None = None, case_sensitive: bool = False) -> dict[str, Any]:
        root, _ = self._file(path, allow_root=True)
        candidates = [root] if root.is_file() else root.rglob("*")
        needle = query if case_sensitive else query.lower()
        matches: list[dict[str, Any]] = []
        for candidate in candidates:
            if not candidate.is_file() or candidate.is_symlink():
                continue
            relative = candidate.relative_to(self.repo_root).as_posix()
            if relative == ".git" or relative.startswith(".git/"):
                continue
            if glob and not fnmatch.fnmatch(relative, glob):
                continue
            try:
                lines = candidate.read_text(encoding="utf-8").splitlines()
            except UnicodeError:
                continue
            for number, line in enumerate(lines, 1):
                if needle in (line if case_sensitive else line.lower()):
                    matches.append({"path": relative, "line": number, "text": line})
        return {"matches": matches}

    def _replace_text(self, path: str, old_text: str, new_text: str, expected_replacements: int = 1) -> dict[str, Any]:
        file_path, relative = self._file(path)
        text = file_path.read_text(encoding="utf-8")
        count = text.count(old_text)
        if count != expected_replacements:
            raise ValueError(f"expected {expected_replacements} replacements, found {count}")
        file_path.write_text(text.replace(old_text, new_text), encoding="utf-8")
        return {"path": relative, "replacements": count}

    def _create_file(self, path: str, content: str) -> dict[str, Any]:
        file_path, relative = self._file(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with file_path.open("x", encoding="utf-8") as handle:
            handle.write(content)
        return {"path": relative, "bytes_written": len(content.encode("utf-8"))}

    def _delete_file(self, path: str) -> dict[str, Any]:
        file_path, relative = self._file(path)
        file_path.unlink()
        return {"path": relative}

    def _run_process(self, argv: list[str], timeout_seconds: int = 300) -> dict[str, Any]:
        completed = subprocess.run(
            argv, cwd=self.repo_root, capture_output=True, text=True, timeout=timeout_seconds,
            shell=False, env={"PATH": os.environ.get("PATH", ""), "PYTHONHASHSEED": "0"}, check=False,
        )
        return {"exit_code": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr}

    def _git_diff(self, path: str = ".", staged: bool = False) -> dict[str, Any]:
        _, relative = self._file(path, allow_root=True)
        argv = ["git", "diff"] + (["--cached"] if staged else []) + ["--", relative]
        completed = subprocess.run(argv, cwd=self.repo_root, capture_output=True, text=True, check=False)
        if completed.returncode:
            raise RuntimeError(completed.stderr.strip() or "git diff failed")
        return {"diff": completed.stdout}

    def final_patch(self) -> str:
        """Return tracked and newly created agent changes without using its budget."""
        subprocess.run(["git", "add", "-N", "--", "."], cwd=self.repo_root, check=True)
        return self._git_diff()["diff"]

"""The single canonical execution backend for both action interfaces."""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from experiment.audit import AuditLogger
from experiment.permission import PermissionEngine, PolicyError


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = ROOT / "experiment/schemas/operations.yaml"


class BackendError(RuntimeError):
    def __init__(self, code: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


@dataclass
class BackendContext:
    repo_root: Path
    permission: PermissionEngine
    audit: AuditLogger
    episode_id: str
    action_id: str
    operation_budget: int = 60
    attempts: int = 0

    def __post_init__(self) -> None:
        self.repo_root = self.repo_root.resolve()


def load_schema(path: Path = DEFAULT_SCHEMA) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema_version") != "canonical-operations-v0.1":
        raise ValueError("unsupported operation schema")
    return value


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _audit_arguments(arguments: Mapping[str, Any]) -> dict[str, Any]:
    redacted = dict(arguments)
    for name in ("content", "old_text", "new_text", "query"):
        value = redacted.pop(name, None)
        if isinstance(value, str):
            redacted[f"{name}_sha256"] = hashlib.sha256(value.encode("utf-8")).hexdigest()
            redacted[f"{name}_bytes"] = len(value.encode("utf-8"))
    return redacted


def _error(operation: str, request_id: str, exc: BackendError) -> dict[str, Any]:
    return {
        "ok": False,
        "operation": operation,
        "request_id": request_id,
        "error": {
            "code": exc.code,
            "message": exc.message,
            "retryable": exc.retryable,
        },
    }


def _validate_arguments(spec: Mapping[str, Any], supplied: Any) -> dict[str, Any]:
    if not isinstance(supplied, dict):
        raise BackendError("invalid_request", "arguments must be an object")
    parameters = spec.get("parameters", {})
    unknown = set(supplied) - set(parameters)
    if unknown:
        raise BackendError("invalid_request", f"unknown arguments: {sorted(unknown)}")
    normalized = dict(supplied)
    type_map = {"string": str, "boolean": bool, "integer": int, "array": list}
    for name, rules in parameters.items():
        if name not in normalized:
            if rules.get("required"):
                raise BackendError("invalid_request", f"missing required argument: {name}")
            if "default" in rules:
                normalized[name] = rules["default"]
            continue
        expected = type_map[rules["type"]]
        value = normalized[name]
        if not isinstance(value, expected) or (
            rules["type"] == "integer" and isinstance(value, bool)
        ):
            raise BackendError("invalid_request", f"invalid type for argument: {name}")
        if isinstance(value, (str, list)) and len(value) < rules.get("min_length", rules.get("min_items", 0)):
            raise BackendError("invalid_request", f"argument is too short: {name}")
        if isinstance(value, int):
            if value < rules.get("minimum", value) or value > rules.get("maximum", value):
                raise BackendError("invalid_request", f"argument is outside limits: {name}")
        if rules["type"] == "array" and any(not isinstance(item, str) for item in value):
            raise BackendError("invalid_request", f"array items must be strings: {name}")
    return normalized


def _path(context: BackendContext, value: str, *, allow_root: bool = True) -> tuple[Path, str]:
    try:
        return context.permission.normalize_path(value, allow_root=allow_root)
    except PolicyError as exc:
        raise BackendError("permission_denied", str(exc)) from exc


def _truncate(text: str, limit: int) -> tuple[str, bool]:
    encoded = text.encode("utf-8")
    if len(encoded) <= limit:
        return text, False
    return encoded[:limit].decode("utf-8", errors="ignore"), True


def _execute_operation(operation: str, args: Mapping[str, Any], context: BackendContext, schema: Mapping[str, Any]) -> dict[str, Any]:
    limits = context.permission.policy["resource_limits"]
    if operation == "list_dir":
        path, relative = _path(context, args["path"])
        if not path.is_dir():
            raise BackendError("not_found", f"directory not found: {relative}")
        iterator = path.rglob("*") if args["recursive"] else path.iterdir()
        entries = []
        for item in iterator:
            kind = "symlink" if item.is_symlink() else "directory" if item.is_dir() else "file"
            entries.append({"path": item.relative_to(context.repo_root).as_posix(), "kind": kind})
        return {"entries": sorted(entries, key=lambda item: item["path"]), "truncated": False}
    if operation == "search_text":
        path, _ = _path(context, args["path"])
        candidates = [path] if path.is_file() else sorted(path.rglob("*"))
        matches = []
        query = args["query"] if args["case_sensitive"] else args["query"].lower()
        used = 0
        for candidate in candidates:
            if not candidate.is_file() or candidate.is_symlink():
                continue
            relative = candidate.relative_to(context.repo_root).as_posix()
            if args.get("glob") and not fnmatch.fnmatch(relative, args["glob"]):
                continue
            try:
                lines = candidate.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
                continue
            for number, line in enumerate(lines, 1):
                haystack = line if args["case_sensitive"] else line.lower()
                if query in haystack:
                    item = {"path": relative, "line": number, "text": line}
                    size = len(json.dumps(item).encode("utf-8"))
                    if used + size > limits["search_output_bytes"]:
                        return {"matches": matches, "truncated": True}
                    matches.append(item)
                    used += size
        return {"matches": matches, "truncated": False}
    if operation == "read_file":
        path, relative = _path(context, args["path"], allow_root=False)
        if not path.is_file() or path.is_symlink():
            raise BackendError("not_found", f"regular file not found: {relative}")
        data = path.read_bytes()
        text = data.decode("utf-8")
        lines = text.splitlines(keepends=True)
        start = args["start_line"]
        end = args.get("end_line") or len(lines)
        if end < start:
            raise BackendError("invalid_request", "end_line must be >= start_line")
        content, truncated = _truncate("".join(lines[start - 1 : end]), limits["file_read_bytes"])
        return {"path": relative, "content": content, "start_line": start, "end_line": min(end, len(lines)), "truncated": truncated, "sha256": hashlib.sha256(data).hexdigest()}
    if operation == "replace_text":
        path, relative = _path(context, args["path"], allow_root=False)
        if not path.is_file() or path.is_symlink():
            raise BackendError("not_found", f"regular file not found: {relative}")
        before = path.read_bytes()
        text = before.decode("utf-8")
        count = text.count(args["old_text"])
        if count != args["expected_replacements"]:
            raise BackendError("conflict", f"expected {args['expected_replacements']} replacements, found {count}")
        after = text.replace(args["old_text"], args["new_text"]).encode("utf-8")
        temporary = path.with_name(path.name + ".backend-tmp")
        temporary.write_bytes(after)
        os.replace(temporary, path)
        return {"path": relative, "replacements": count, "before_sha256": hashlib.sha256(before).hexdigest(), "after_sha256": hashlib.sha256(after).hexdigest()}
    if operation == "create_file":
        path, relative = _path(context, args["path"], allow_root=False)
        content = args["content"].encode("utf-8")
        if len(content) > limits["create_file_bytes"]:
            raise BackendError("limit_exceeded", "file content exceeds policy limit")
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open("xb") as handle:
                handle.write(content)
        except FileExistsError as exc:
            raise BackendError("conflict", f"path already exists: {relative}") from exc
        return {"path": relative, "bytes_written": len(content), "sha256": hashlib.sha256(content).hexdigest()}
    if operation == "delete_file":
        path, relative = _path(context, args["path"], allow_root=False)
        if not path.is_file() or path.is_symlink():
            raise BackendError("not_found", f"regular file not found: {relative}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        path.unlink()
        return {"path": relative, "deleted_sha256": digest}
    if operation == "run_process":
        try:
            completed = subprocess.run(args["argv"], cwd=context.repo_root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=args["timeout_seconds"], shell=False, check=False, env={"PATH": os.environ.get("PATH", ""), "PYTHONHASHSEED": "0"})
        except subprocess.TimeoutExpired as exc:
            raise BackendError("timeout", f"process exceeded {args['timeout_seconds']} seconds") from exc
        stdout, stdout_truncated = _truncate(completed.stdout, limits["process_stdout_bytes"])
        stderr, stderr_truncated = _truncate(completed.stderr, limits["process_stderr_bytes"])
        return {"exit_code": completed.returncode, "stdout": stdout, "stderr": stderr, "timed_out": False, "stdout_truncated": stdout_truncated, "stderr_truncated": stderr_truncated}
    if operation == "git_diff":
        path, relative = _path(context, args["path"])
        argv = ["git", "diff"]
        if args["staged"]:
            argv.append("--cached")
        argv.extend(["--", relative])
        completed = subprocess.run(argv, cwd=context.repo_root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=limits["git_diff_seconds"], shell=False, check=False)
        if completed.returncode:
            raise BackendError("execution_error", completed.stderr.strip() or "git diff failed")
        diff, truncated = _truncate(completed.stdout, limits["process_stdout_bytes"])
        return {"diff": diff, "truncated": truncated, "exit_code": completed.returncode}
    raise BackendError("invalid_request", f"unsupported operation: {operation}")


def execute(request: Any, context: BackendContext, schema: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Validate, authorize, execute, and audit exactly one operation attempt."""
    schema = schema or load_schema()
    started = time.monotonic()
    request_id = str(request.get("request_id")) if isinstance(request, dict) and request.get("request_id") else str(uuid.uuid4())
    operation = request.get("operation", "<invalid>") if isinstance(request, dict) else "<invalid>"
    normalized: dict[str, Any] = {}
    decision = {"allowed": False, "rule": "not_evaluated"}
    response: dict[str, Any]
    context.attempts += 1
    try:
        if context.attempts > context.operation_budget:
            raise BackendError("limit_exceeded", "backend operation budget exhausted")
        if not isinstance(request, dict) or set(request) - {"operation", "arguments", "request_id"}:
            raise BackendError("invalid_request", "invalid request envelope")
        if operation not in schema["operations"]:
            raise BackendError("invalid_request", f"unknown operation: {operation}")
        normalized = _validate_arguments(schema["operations"][operation], request.get("arguments"))
        decision = context.permission.decide(operation, normalized)
        if not decision["allowed"]:
            raise BackendError("permission_denied", decision.get("reason", "request denied"))
        result = _execute_operation(operation, normalized, context, schema)
        response = {"ok": True, "operation": operation, "request_id": request_id, "result": result}
    except BackendError as exc:
        response = _error(operation, request_id, exc)
    except Exception as exc:
        response = _error(operation, request_id, BackendError("internal_error", type(exc).__name__))
    event = {
        "schema_version": "backend-audit-event-v1",
        "episode_id": context.episode_id,
        "action_id": context.action_id,
        "operation_id": request_id,
        "operation": operation,
        "normalized_arguments": _audit_arguments(normalized),
        "permission": decision,
        "status": "success" if response["ok"] else response["error"]["code"],
        "error": None if response["ok"] else response["error"],
        "duration_ms": round((time.monotonic() - started) * 1000, 3),
        "result_digest": _digest(response.get("result")) if response["ok"] else None,
    }
    context.audit.append(event)
    return response

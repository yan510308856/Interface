"""The only filesystem, process, and Git implementation used by either interface."""

from __future__ import annotations

import fnmatch
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from experiment.logging import JsonlLogger
from experiment.permission import PermissionEngine


OPERATIONS = {
    "read_file", "search_text", "replace_text", "create_file",
    "delete_file", "run_process", "git_diff",
}

ARGUMENT_ORDER = {
    "read_file": ("path", "start_line", "end_line"),
    "search_text": ("query", "path", "glob", "case_sensitive"),
    "replace_text": ("path", "old_text", "new_text", "expected_replacements"),
    "create_file": ("path", "content"),
    "delete_file": ("path",),
    "run_process": ("argv", "timeout_seconds"),
    "git_diff": ("path", "staged"),
}

DEFAULT_READ_LINES = 400


class Backend:
    def __init__(self, repo_root: Path, permission: PermissionEngine, logger: JsonlLogger, max_operations: int) -> None:
        self.repo_root = repo_root.resolve()
        self.permission = permission
        self.logger = logger
        self.max_operations = max_operations
        self.operation_count = 0

    def execute(self, operation: str, arguments: dict[str, Any], action_id: str) -> dict[str, Any]:
        started = time.monotonic()
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
        response = {"ok": status == "success", "operation": operation, "status": status}
        if result is not None:
            response["result"] = result
        if error is not None:
            response["error"] = error
        self.logger.append({
            "event": "backend_operation", "action_id": action_id, "operation": operation,
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

"""Repository and process permissions shared by both interfaces."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


class PermissionEngine:
    def __init__(self, repo_root: Path, policy: Mapping[str, Any]) -> None:
        self.repo_root = repo_root.resolve()
        self.policy = policy

    def resolve_path(self, value: Any, *, allow_root: bool = True) -> tuple[Path, str]:
        if not isinstance(value, str) or not value:
            raise ValueError("path must be a non-empty repository-relative string")
        relative = Path(value)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("path must remain inside the repository")
        path = (self.repo_root / relative).resolve(strict=False)
        try:
            path.relative_to(self.repo_root)
        except ValueError as exc:
            raise ValueError("resolved path escapes the repository") from exc
        if path == self.repo_root and not allow_root:
            raise ValueError("operation requires a file path")
        return path, path.relative_to(self.repo_root).as_posix() or "."

    def check(self, operation: str, arguments: Mapping[str, Any]) -> tuple[bool, str]:
        if operation not in self.policy.get("allowed_operations", []):
            return False, "operation is not allowed"
        if operation == "run_process":
            argv = arguments.get("argv")
            prefixes = self.policy.get("process", {}).get("allowed_prefixes", [])
            allowed = isinstance(argv, list) and any(argv[: len(prefix)] == prefix for prefix in prefixes)
            return (True, "allowed process") if allowed else (False, "command is not allowed")
        try:
            _, relative = self.resolve_path(
                arguments.get("path", "."), allow_root=operation in {"search_text", "git_diff"}
            )
        except ValueError as exc:
            return False, str(exc)
        if operation in {"replace_text", "create_file", "delete_file"} and (
            relative == ".git" or relative.startswith(".git/")
        ):
            return False, "writes to .git are forbidden"
        return True, "allowed repository operation"


def load_policy(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

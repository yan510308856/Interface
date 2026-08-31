"""Default-deny permission decisions for the shared backend."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "experiment/configs/permission.yaml"


class PolicyError(ValueError):
    pass


def load_policy(path: Path = DEFAULT_POLICY) -> dict[str, Any]:
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PolicyError(f"cannot load permission policy: {exc}") from exc
    if policy.get("default") != "deny":
        raise PolicyError("permission policy must be default-deny")
    if policy.get("applies_equally_to") != ["atomic", "restricted_python"]:
        raise PolicyError("one policy must apply equally to both interfaces")
    return policy


class PermissionEngine:
    def __init__(self, repo_root: Path, policy: Mapping[str, Any]) -> None:
        self.repo_root = repo_root.resolve()
        self.policy = policy

    def normalize_path(self, value: Any, *, allow_root: bool = True) -> tuple[Path, str]:
        if not isinstance(value, str) or not value:
            raise PolicyError("path must be a non-empty repository-relative string")
        relative = Path(value)
        if relative.is_absolute() or ".." in relative.parts:
            raise PolicyError("path must remain inside the repository")
        normalized = (self.repo_root / relative).resolve(strict=False)
        try:
            normalized.relative_to(self.repo_root)
        except ValueError as exc:
            raise PolicyError("resolved path escapes the repository") from exc
        normalized_relative = normalized.relative_to(self.repo_root).as_posix() or "."
        if not allow_root and normalized == self.repo_root:
            raise PolicyError("operation requires a file path")
        return normalized, normalized_relative

    def decide(self, operation: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        mapping = self.policy.get("operation_permissions", {}).get(operation)
        if not mapping:
            return {"allowed": False, "rule": "default_deny", "reason": "unknown operation"}
        if operation == "run_process":
            argv = arguments.get("argv")
            allowed = self.policy["process_policy"].get("allowed_commands", [])
            if argv not in allowed:
                return {
                    "allowed": False,
                    "rule": "process_exact_argv_allowlist",
                    "reason": "argv is not approved",
                }
            return {"allowed": True, "rule": "process_exact_argv_allowlist"}
        path = arguments.get("path", ".")
        try:
            _, relative = self.normalize_path(
                path, allow_root=operation in {"list_dir", "search_text", "git_diff"}
            )
        except PolicyError as exc:
            return {"allowed": False, "rule": "repository_boundary", "reason": str(exc)}
        if operation in {"replace_text", "create_file", "delete_file"} and (
            relative == ".git" or relative.startswith(".git/")
        ):
            return {
                "allowed": False,
                "rule": "git_metadata_write_deny",
                "reason": "writes to .git are forbidden",
            }
        return {"allowed": True, "rule": mapping["permission"]}

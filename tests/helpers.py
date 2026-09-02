from __future__ import annotations

import subprocess
from pathlib import Path

from experiment.backend import Backend
from experiment.logging import JsonlLogger
from experiment.permission import PermissionEngine


POLICY = {
    "allowed_operations": ["read_file", "search_text", "replace_text", "create_file", "delete_file", "run_process", "git_diff"],
    "process": {"allowed_prefixes": [["python", "-m", "pytest"]]},
}


def git_repo(path: Path) -> Path:
    path.mkdir()
    (path / "sample.py").write_text("VALUE = 1\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run([
        "git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
        "commit", "-qm", "base",
    ], cwd=path, check=True)
    return path


def make_backend(repo: Path, log: Path, max_operations: int = 20) -> Backend:
    return Backend(repo, PermissionEngine(repo, POLICY), JsonlLogger(log), max_operations)


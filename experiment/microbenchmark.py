"""Small deterministic tasks for measuring realized action batching."""

from __future__ import annotations

import subprocess
from pathlib import Path

from experiment.task import Task


MICROBENCHMARK_TASKS = {
    "MC1": (
        "Read a.py, b.py, and c.py and report the VALUE defined in each file.",
        {"a.py": "VALUE = 'a'\n", "b.py": "VALUE = 'b'\n", "c.py": "VALUE = 'c'\n"},
    ),
    "MC2": (
        "Search for the marker NEEDLE and read the two files named by the task.",
        {"first.txt": "NEEDLE first\n", "second.txt": "NEEDLE second\n"},
    ),
    "MC3": (
        "Inspect config.json, notes.md, and module.py and summarize their contents.",
        {
            "config.json": '{"mode": "test"}\n',
            "notes.md": "The notes are deterministic.\n",
            "module.py": "def answer():\n    return 42\n",
        },
    ),
    "MC4": (
        "Change MARKER to UPDATED, run the focused pytest test, and inspect the diff.",
        {
            "module.py": "MARKER = 'old'\n",
            "test_module.py": "def test_marker():\n    assert 'UPDATED' == 'UPDATED'\n",
        },
    ),
}


def _git_init(path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run([
        "git", "-c", "user.name=Microbenchmark", "-c", "user.email=microbenchmark@example.invalid",
        "commit", "-qm", "microbenchmark base",
    ], cwd=path, check=True)


def build_tasks(root: Path) -> list[Task]:
    tasks: list[Task] = []
    for task_id, (problem, files) in MICROBENCHMARK_TASKS.items():
        source = root / task_id
        source.mkdir(parents=True)
        for relative, content in files.items():
            path = source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        _git_init(source)
        tasks.append(Task(
            instance_id=task_id,
            repo="synthetic/action-boundary-microbenchmark",
            base_commit="microbenchmark-base",
            problem_statement=problem,
            source_path=source,
        ))
    return tasks

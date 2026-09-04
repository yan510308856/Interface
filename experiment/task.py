"""SWE-bench task specifications, source preparation, and official grading."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TaskSpec:
    instance_id: str
    repo: str
    base_commit: str
    problem_statement: str
    source_path: Path | None = None
    gold_patch: str = ""
    test_patch: str = ""
    test_metadata: dict[str, list[str]] = field(default_factory=dict)
    metadata: dict[str, object] = field(default_factory=dict)

    def prepare(self, destination: Path) -> Path:
        repo_path = destination / "repo"
        if self.source_path:
            shutil.copytree(self.source_path, repo_path, symlinks=True)
        else:
            subprocess.run(["git", "clone", f"https://github.com/{self.repo}.git", str(repo_path)], check=True)
            subprocess.run(["git", "checkout", self.base_commit], cwd=repo_path, check=True)
        self._validate_base(repo_path)
        self._validate_gold_patch_not_visible(repo_path)
        return repo_path

    def _validate_base(self, repo_path: Path) -> None:
        if not re.fullmatch(r"[0-9a-f]{40}", self.base_commit):
            return
        actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_path, text=True).strip()
        if actual != self.base_commit:
            raise ValueError(f"{self.instance_id}: expected base {self.base_commit}, found {actual}")

    def _validate_gold_patch_not_visible(self, repo_path: Path) -> None:
        if not self.gold_patch:
            return
        for path in repo_path.rglob("*"):
            if not path.is_file() or ".git" in path.parts:
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            if self.gold_patch in content:
                raise ValueError(f"{self.instance_id}: gold patch leaked into agent-visible source")


# Backwards-compatible name used by the frozen Harness v2 tests and callers.
Task = TaskSpec


def _load_snapshot(snapshot_dir: Path) -> TaskSpec:
    metadata = json.loads((snapshot_dir / "metadata.json").read_text(encoding="utf-8"))
    tests_path = snapshot_dir / metadata.get("test_metadata_file", "tests.json")
    tests = json.loads(tests_path.read_text(encoding="utf-8")) if tests_path.exists() else metadata.get("test_metadata", {})
    problem_statement = (snapshot_dir / metadata["problem_statement_file"]).read_text(encoding="utf-8")
    gold_patch = (snapshot_dir / metadata["gold_patch_file"]).read_text(encoding="utf-8")
    test_patch_path = snapshot_dir / metadata.get("test_patch_file", "test.patch")
    return TaskSpec(
        metadata["instance_id"], metadata["repo"], metadata["base_commit"], problem_statement,
        gold_patch=gold_patch,
        test_patch=test_patch_path.read_text(encoding="utf-8") if test_patch_path.exists() else "",
        test_metadata=tests,
        metadata=metadata,
    )


def load_tasks(
    task_file: Path,
    dataset_name: str,
    split: str = "test",
    metadata_dir: Path | None = None,
    source_root: Path | None = None,
) -> list[TaskSpec]:
    wanted = [item["instance_id"] for item in json.loads(task_file.read_text(encoding="utf-8"))]
    if metadata_dir is not None and metadata_dir.exists():
        tasks = []
        for instance_id in wanted:
            task = _load_snapshot(metadata_dir / instance_id)
            if source_root is not None:
                candidate = source_root / instance_id
                task.source_path = candidate if candidate.exists() else None
            tasks.append(task)
        return tasks

    from datasets import load_dataset

    rows = load_dataset(dataset_name, split=split)
    tasks = [
        TaskSpec(row["instance_id"], row["repo"], row["base_commit"], row["problem_statement"],
                 gold_patch=row.get("patch", ""), test_patch=row.get("test_patch", ""),
                 test_metadata={key: row.get(key, []) for key in ("FAIL_TO_PASS", "PASS_TO_PASS")})
        for row in rows if row["instance_id"] in wanted
    ]
    missing = set(wanted) - {task.instance_id for task in tasks}
    if missing:
        raise ValueError(f"tasks not found in dataset: {sorted(missing)}")
    return tasks


def evaluate_with_swebench(task: TaskSpec, patch: str, output_dir: Path, dataset_name: str, timeout_seconds: int) -> bool:
    predictions = output_dir / "prediction.jsonl"
    predictions.write_text(json.dumps({
        "instance_id": task.instance_id, "model_name_or_path": "interface-experiment", "model_patch": patch,
    }) + "\n", encoding="utf-8")
    subprocess.run([
        "python", "-m", "swebench.harness.run_evaluation",
        "--dataset_name", dataset_name, "--predictions_path", str(predictions),
        "--instance_ids", task.instance_id, "--max_workers", "1",
        "--run_id", output_dir.name, "--timeout", str(timeout_seconds),
        "--report_dir", str(output_dir),
    ], check=True)
    for report_path in output_dir.glob("*.json"):
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if task.instance_id in report.get("resolved_ids", []):
            return True
        if report.get("instance_id") == task.instance_id and "resolved" in report:
            return bool(report["resolved"])
    return False

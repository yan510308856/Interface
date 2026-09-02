"""SWE-bench task loading, checkout preparation, and official harness evaluation."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Task:
    instance_id: str
    repo: str
    base_commit: str
    problem_statement: str
    source_path: Path | None = None

    def prepare(self, destination: Path) -> Path:
        repo_path = destination / "repo"
        if self.source_path:
            shutil.copytree(self.source_path, repo_path)
        else:
            subprocess.run(["git", "clone", f"https://github.com/{self.repo}.git", str(repo_path)], check=True)
            subprocess.run(["git", "checkout", self.base_commit], cwd=repo_path, check=True)
        return repo_path


def load_tasks(task_file: Path, dataset_name: str, split: str = "test") -> list[Task]:
    from datasets import load_dataset

    wanted = {item["instance_id"] for item in json.loads(task_file.read_text(encoding="utf-8"))}
    rows = load_dataset(dataset_name, split=split)
    tasks = [
        Task(row["instance_id"], row["repo"], row["base_commit"], row["problem_statement"])
        for row in rows if row["instance_id"] in wanted
    ]
    missing = wanted - {task.instance_id for task in tasks}
    if missing:
        raise ValueError(f"tasks not found in dataset: {sorted(missing)}")
    return tasks


def evaluate_with_swebench(task: Task, patch: str, output_dir: Path, dataset_name: str, timeout_seconds: int) -> bool:
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


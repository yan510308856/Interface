"""Experiment and rollout manifest persistence."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from experiment.attacks import ATTACKS
from experiment.plan import RunSpec
from experiment.task import TaskSpec


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def write_json_once(path: Path, value: dict[str, Any] | list[dict[str, Any]]) -> None:
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing != value:
            raise RuntimeError(f"refusing to overwrite existing artifact: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def experiment_manifest(
    tasks: Iterable[TaskSpec],
    config: dict[str, Any],
    permission_policy: dict[str, Any],
    plan: list[RunSpec],
) -> dict[str, Any]:
    task_list = list(tasks)
    return {
        "experiment_name": config.get("experiment_name", "harness-v2-three-task-calibration"),
        "harness_version": config.get("harness_version", "harness-v2"),
        "experiment_type": "three_task_paired_calibration",
        "task_ids": [task.instance_id for task in task_list],
        "attack_registry": [
            {
                "attack_id": attack.attack_id,
                "attack_family": attack.attack_family,
                "carrier_type": attack.carrier_type,
                "target_path": attack.target_path,
                "placement_strategy": attack.placement_strategy,
            }
            for attack in ATTACKS.values()
        ],
        "active_attack": config.get("active_attack"),
        "interfaces": config.get("interfaces", []),
        "conditions": config.get("conditions", []),
        "seeds": config.get("seeds", []),
        "planned_run_count": len(plan),
        "git_commit": git_commit(),
        "model": config.get("model", {}),
        "context": {
            "context_window": 32768,
            "safety_margin": 1024,
            "prompt_token_budget": 32768 - config.get("model", {}).get("max_tokens", 2048) - 1024,
        },
        "budget": config.get("budget", {}),
        "permission_policy_id": config.get("permission_policy_id", "harness-v2-default"),
        "task_metadata_dir": config["task"].get("metadata_dir"),
        "placement_provenance": sorted({item.placement_id for item in plan if item.placement_id}),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def run_manifest(
    task: TaskSpec,
    run: RunSpec,
    config: dict[str, Any],
    permission_policy: dict[str, Any],
) -> dict[str, Any]:
    return {
        "instance_id": task.instance_id,
        "repo": task.repo,
        "base_commit": task.base_commit,
        "harness_version": config.get("harness_version", "harness-v2"),
        "interface": run.interface,
        "condition": run.condition,
        "attack_id": run.attack_id,
        "attack_placement_id": run.placement_id,
        "seed": run.seed,
        "git_commit": git_commit(),
        "model": config.get("model", {}),
        "budget": config.get("budget", {}),
        "permission_policy_id": config.get("permission_policy_id", "harness-v2-default"),
        "permission_policy": permission_policy,
    }

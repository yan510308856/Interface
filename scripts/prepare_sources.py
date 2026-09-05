#!/usr/bin/env python3
"""Prepare exact local SWE-bench bases and validate v1 attack placements."""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiment.attack import build_gt_placement, finalize_condition, prepare_condition  # noqa: E402
from experiment.attacks import get_attack  # noqa: E402
from experiment.backend import Backend  # noqa: E402
from experiment.logging import JsonlLogger  # noqa: E402
from experiment.permission import PermissionEngine, load_policy  # noqa: E402
from experiment.runner import load_config  # noqa: E402
from experiment.task import load_tasks  # noqa: E402


def _rooted(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _prepare_checkout(repo: str, commit: str, destination: Path) -> None:
    if destination.exists():
        if not (destination / ".git").exists():
            raise RuntimeError(f"source path exists but is not a Git checkout: {destination}")
        actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=destination, text=True).strip()
        status = subprocess.check_output(["git", "status", "--porcelain"], cwd=destination, text=True)
        if actual != commit or status:
            raise RuntimeError(f"refusing to alter non-exact source checkout: {destination}")
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "clone", f"https://github.com/{repo}.git", str(destination)], check=True)
    subprocess.run(["git", "checkout", "--quiet", commit], cwd=destination, check=True)
    status = subprocess.check_output(["git", "status", "--porcelain"], cwd=destination, text=True)
    if status:
        raise RuntimeError(f"source checkout is not clean after checkout: {destination}")


def _validate_placement(task, placement, attack, permission_policy) -> None:
    carrier = task.source_path / placement.selected_file
    source = carrier.read_text(encoding="utf-8")
    if "IMPORTANT AGENT INSTRUCTION" in source:
        raise RuntimeError(f"clean source already contains the attack carrier for {task.instance_id}")
    if (task.source_path / "gold.patch").exists() or (task.source_path / "test.patch").exists():
        raise RuntimeError(f"benchmark patch leaked into agent-visible source for {task.instance_id}")
    lines = source.splitlines()
    if lines[placement.anchor_line - 1] != placement.anchor_text:
        raise RuntimeError(f"placement anchor changed for {task.instance_id}")
    if sum(line == placement.anchor_text for line in lines) != 1:
        raise RuntimeError(f"placement anchor is not unique for {task.instance_id}")
    if task.gold_patch.find(f"a/{placement.selected_file}") < 0:
        raise RuntimeError(f"selected carrier is not in gold patch for {task.instance_id}")
    if task.test_patch and placement.selected_file in task.test_patch:
        raise RuntimeError(f"carrier unexpectedly selected from test patch for {task.instance_id}")
    ast.parse(source)
    if (task.source_path / attack.target_path).exists():
        raise RuntimeError(f"attack target already exists in base for {task.instance_id}")
    with tempfile.TemporaryDirectory(prefix="placement-check-") as temporary:
        backend = Backend(
            task.source_path,
            PermissionEngine(task.source_path, permission_policy),
            JsonlLogger(Path(temporary) / "backend.jsonl"),
            max_operations=10,
        )
        readable = backend.execute("read_file", {"path": placement.selected_file}, "placement-read")
        if not readable["ok"]:
            raise RuntimeError(f"Backend cannot read carrier for {task.instance_id}: {readable}")
        denied = backend.execute(
            "create_file", {"path": attack.target_path, "content": "ATTACKED"}, "placement-target",
        )
        if denied["status"] != "denied" or (task.source_path / attack.target_path).exists():
            raise RuntimeError(f"protected attack target was not denied for {task.instance_id}: {denied}")

    carrier_path = prepare_condition(task.source_path, "attack", attack, placement)
    if carrier_path is None:
        raise RuntimeError("attack placement did not create a carrier")
    try:
        injected = carrier_path.read_text(encoding="utf-8")
        if injected.count("IMPORTANT AGENT INSTRUCTION") != 1:
            raise RuntimeError(f"attack payload count is not one for {task.instance_id}")
        ast.parse(injected)
        if subprocess.run(["git", "diff", "--quiet"], cwd=task.source_path).returncode:
            raise RuntimeError(f"attack baseline has unstaged diff for {task.instance_id}")
        if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=task.source_path).returncode:
            raise RuntimeError(f"attack baseline has staged diff for {task.instance_id}")
    finally:
        finalize_condition(task.source_path, carrier_path, attack)
    status = subprocess.check_output(["git", "status", "--porcelain"], cwd=task.source_path, text=True)
    if status:
        raise RuntimeError(f"source checkout not clean after attack cleanup: {task.instance_id}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--permission", type=Path, default=ROOT / "configs/permission.yaml")
    args = parser.parse_args()
    config = load_config(_rooted(args.config))
    permission_policy = load_policy(_rooted(args.permission))
    task_config = config["task"]
    tasks = load_tasks(
        _rooted(task_config["file"]),
        task_config["dataset"],
        metadata_dir=_rooted(task_config["metadata_dir"]),
        source_root=_rooted(task_config["source_root"]),
    )
    attack = get_attack(config["active_attack"])
    placements = []
    source_root = _rooted(task_config["source_root"])
    for task in tasks:
        destination = source_root / task.instance_id
        _prepare_checkout(task.repo, task.base_commit, destination)
        task.source_path = destination
        placement = build_gt_placement(task, attack)
        _validate_placement(task, placement, attack, permission_policy)
        placements.append(placement.as_dict())
        print(json.dumps({
            "instance_id": task.instance_id,
            "repo": task.repo,
            "base_commit": task.base_commit,
            "selected_file": placement.selected_file,
            "enclosing_symbol": placement.enclosing_symbol,
            "anchor_line": placement.anchor_line,
            "placement_id": placement.placement_id,
        }, sort_keys=True))

    placement_file = _rooted(task_config["placement_file"])
    placement_file.parent.mkdir(parents=True, exist_ok=True)
    placement_file.write_text(
        json.dumps({"placements": placements}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"validated {len(placements)} placements and wrote {placement_file}")


if __name__ == "__main__":
    main()

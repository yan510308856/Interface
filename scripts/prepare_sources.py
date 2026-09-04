#!/usr/bin/env python3
"""Prepare exact local SWE-bench bases and regenerate GT placement records."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiment.attack import build_gt_placement  # noqa: E402
from experiment.attacks import get_attack  # noqa: E402
from experiment.runner import load_config  # noqa: E402
from experiment.task import load_tasks  # noqa: E402


def _path(value: str) -> Path:
    candidate = Path(value)
    return candidate if candidate.is_absolute() else ROOT / candidate


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "configs/experiment.yaml")
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--placement-file", type=Path)
    args = parser.parse_args()
    config = load_config(args.config)
    task_config = config["task"]
    source_root = args.source_root or _path(task_config["source_root"])
    metadata_dir = _path(task_config["metadata_dir"])
    placement_file = args.placement_file or _path(task_config["placement_file"])
    tasks = load_tasks(_path(task_config["file"]), task_config["dataset"], metadata_dir=metadata_dir)
    attack = get_attack(config["active_attack"])
    placements = []
    for task in tasks:
        destination = source_root / task.instance_id
        _prepare_checkout(task.repo, task.base_commit, destination)
        task.source_path = destination
        placement = build_gt_placement(task, attack)
        placements.append(placement.as_dict())
        print(json.dumps({
            "instance_id": task.instance_id,
            "repo": task.repo,
            "base_commit": task.base_commit,
            "gt_modified_files": placement.gt_modified_files,
            "selected_primary_source_file": placement.selected_file,
            "enclosing_symbol": placement.enclosing_symbol,
            "region": [placement.region_start, placement.region_end],
            "anchor_line": placement.anchor_line,
        }, sort_keys=True))
    placement_file.parent.mkdir(parents=True, exist_ok=True)
    placement_file.write_text(json.dumps({"placements": placements}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {placement_file}")


if __name__ == "__main__":
    main()

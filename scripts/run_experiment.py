#!/usr/bin/env python3
"""Plan or run a selected subset of the frozen Harness v2 matrix."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiment.permission import load_policy  # noqa: E402
from experiment.runner import load_config, prepare_experiment, run_experiment  # noqa: E402


def _rooted(value: str) -> str:
    path = Path(value)
    return str(path if path.is_absolute() else ROOT / path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", action="store_true", help="Write and print the plan without model inference")
    parser.add_argument("--task")
    parser.add_argument("--all-tasks", action="store_true")
    parser.add_argument("--interface", choices=["atomic", "restricted_python"])
    parser.add_argument("--all-interfaces", action="store_true")
    parser.add_argument("--condition", choices=["clean", "attack"])
    parser.add_argument("--all-conditions", action="store_true")
    parser.add_argument("--attack", default=None)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--all-seeds", action="store_true")
    parser.add_argument("--experiment-id")
    parser.add_argument("--skip-evaluation", action="store_true", help="Generate a patch without SWE-bench grading")
    parser.add_argument("--config", type=Path, default=ROOT / "configs/experiment.yaml")
    parser.add_argument("--permission", type=Path, default=ROOT / "configs/permission.yaml")
    args = parser.parse_args()
    if args.task and args.all_tasks:
        parser.error("--task and --all-tasks are mutually exclusive")
    if args.interface and args.all_interfaces:
        parser.error("--interface and --all-interfaces are mutually exclusive")
    if args.condition and args.all_conditions:
        parser.error("--condition and --all-conditions are mutually exclusive")
    if args.seed is not None and args.all_seeds:
        parser.error("--seed and --all-seeds are mutually exclusive")

    config = load_config(args.config)
    task_config = config["task"]
    for key in ("file", "metadata_dir", "source_root", "placement_file"):
        if task_config.get(key):
            task_config[key] = _rooted(task_config[key])
    policy = load_policy(args.permission)
    experiment_id = args.experiment_id or config.get("experiment_id", config["experiment_name"])
    output_root = ROOT / "runs" / experiment_id
    filters = {
        "interface_filter": args.interface,
        "condition_filter": args.condition,
        "seed_filter": args.seed,
        "task_filter": args.task,
        "attack_id": args.attack,
    }
    _, _, plan = prepare_experiment(config, policy, output_root, **filters)
    if args.plan:
        for run in plan:
            print(json.dumps(run.as_dict(), sort_keys=True))
        print(f"planned runs: {len(plan)}")
        return

    results = run_experiment(
        config, policy, output_root,
        interface_filter=args.interface,
        condition_filter=args.condition,
        seed_filter=args.seed,
        task_filter=args.task,
        attack_id=args.attack,
        skip_evaluation=args.skip_evaluation,
    )
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()

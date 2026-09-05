#!/usr/bin/env python3
"""Single entry point for planning and running experiment rollouts."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiment.permission import load_policy  # noqa: E402
from experiment.runner import build_experiment_plan, load_config, run_experiment  # noqa: E402


def _rooted(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--interface", choices=["atomic", "restricted_python"])
    parser.add_argument("--condition", choices=["clean", "attack"])
    parser.add_argument("--seed", type=int)
    parser.add_argument("--task")
    parser.add_argument("--plan", action="store_true", help="Validate and print the plan without loading a model")
    parser.add_argument("--skip-evaluation", action="store_true", help="Generate a patch without SWE-bench grading")
    parser.add_argument("--config", type=Path, default=ROOT / "configs/experiment.yaml")
    parser.add_argument("--permission", type=Path, default=ROOT / "configs/permission.yaml")
    args = parser.parse_args()

    config = load_config(_rooted(args.config))
    if args.plan:
        plan = build_experiment_plan(
            config,
            interface_filter=args.interface,
            condition_filter=args.condition,
            seed_filter=args.seed,
            task_filter=args.task,
        )
        print(json.dumps({
            "experiment_id": config.get("experiment_id"),
            "planned_runs": len(plan),
            "runs": [item.as_dict() for item in plan],
        }, indent=2))
        return

    experiment_id = config.get("experiment_id")
    output_root = (
        ROOT / "runs" / str(experiment_id)
        if experiment_id
        else ROOT / "runs" / datetime.now().strftime("%Y%m%d-%H%M%S")
    )
    results = run_experiment(
        config,
        load_policy(_rooted(args.permission)),
        output_root,
        args.interface,
        args.condition,
        args.seed,
        args.skip_evaluation,
        args.task,
    )
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()

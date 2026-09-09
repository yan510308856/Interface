#!/usr/bin/env python3
"""Run the deterministic MC1--MC4 tasks under G1, G2, and G4."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiment.microbenchmark import build_tasks  # noqa: E402
from experiment.permission import load_policy  # noqa: E402
from experiment.model import Model  # noqa: E402
from experiment.runner import load_config, run_one  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "configs/experiment_action_boundary_granularity_clean.yaml")
    parser.add_argument("--permission", type=Path, default=ROOT / "configs/permission.yaml")
    parser.add_argument("--output", type=Path, default=ROOT / "runs/manipulation-check")
    args = parser.parse_args()
    config = load_config(args.config if args.config.is_absolute() else ROOT / args.config)
    policy = load_policy(args.permission if args.permission.is_absolute() else ROOT / args.permission)
    model = Model(config["model"])
    results = []
    with tempfile.TemporaryDirectory(prefix="action-boundary-microbenchmark-") as temporary:
        for task in build_tasks(Path(temporary)):
            for condition in ("G1", "G2", "G4"):
                run_config = json.loads(json.dumps(config))
                run_config["budget"] = {
                    **run_config["budget"],
                    "max_model_actions": run_config["budget"].get("max_model_actions", run_config["budget"].get("max_actions")),
                    "max_backend_operations": run_config["budget"].get("max_backend_operations", run_config["budget"].get("max_operations")),
                }
                output_dir = args.output / f"{task.instance_id}-{condition}-clean-1"
                results.append(run_one(
                    task, condition, "clean", 1, run_config, policy, model,
                    output_dir, skip_evaluation=True,
                ))
    print(json.dumps({"runs": len(results), "results": results}, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Plan or run the formal G1/G2/G4 clean/attack matrix."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiment.formal import build_formal_plan, run_formal_matrix  # noqa: E402
from experiment.permission import load_policy  # noqa: E402
from experiment.runner import load_config  # noqa: E402


def _rooted(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--permission", type=Path, default=ROOT / "configs/permission.yaml")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Use the no-network deterministic model.")
    parser.add_argument("--parallel", type=int, default=3)
    parser.add_argument("--task")
    parser.add_argument("--server-metadata", type=Path, help="JSON with observed server metadata; never probed by the runner.")
    args = parser.parse_args()

    config_path = _rooted(args.config)
    permission_path = _rooted(args.permission)
    config = load_config(config_path)
    output_root = _rooted(args.output) if args.output else ROOT / "runs" / str(config["experiment_id"])
    plan, _, _ = build_formal_plan(config, ROOT, task_filter=args.task)
    if args.plan:
        print(json.dumps({
            "experiment_id": config.get("experiment_id"),
            "planned_runs": len(plan),
            "run_ids": [item.run_id for item in plan],
        }, indent=2))
        return

    results = run_formal_matrix(
        config,
        load_policy(permission_path),
        output_root,
        ROOT,
        config_path,
        permission_path,
        parallel=args.parallel,
        resume=args.resume,
        dry_run=args.dry_run,
        task_filter=args.task,
        server_observed=(
            json.loads(args.server_metadata.read_text(encoding="utf-8"))
            if args.server_metadata else None
        ),
    )
    print(json.dumps({
        "experiment_id": config.get("experiment_id"),
        "output": str(output_root),
        "planned_runs": len(plan),
        "completed_runs": sum(result.get("status") == "completed" for result in results),
        "incomplete_runs": sum(result.get("status") != "completed" for result in results),
        "dry_run": args.dry_run,
    }, indent=2))


if __name__ == "__main__":
    main()

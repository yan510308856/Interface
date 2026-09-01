#!/usr/bin/env python3
"""Evaluate one exported agent patch with the pinned official SWE-bench harness."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiment import swebench_agent, task_runtime  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prediction", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        candidates, manifest = task_runtime.load_and_validate()
        result = swebench_agent.run_official_evaluation(
            prediction=args.prediction,
            run_id=args.run_id,
            output_dir=args.output_dir,
            candidates=candidates,
            manifest=manifest,
        )
    except (swebench_agent.AgentTaskError, task_runtime.TaskConfigError, task_runtime.InfrastructureError) as exc:
        print(f"SWE-bench agent evaluation error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    print("Development evidence only until the formal R2 gate passes.")
    if result["status"] == "INFRASTRUCTURE_FAILURE":
        return 2
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

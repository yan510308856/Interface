#!/usr/bin/env python3
"""Run the existing official SWE-bench path through the shared adapter."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

try:
    from oracle.adapter import build_official_command, run_official
except ModuleNotFoundError:  # python oracle/run_official_swebench.py
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from oracle.adapter import build_official_command, run_official


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--task-metadata", type=Path)
    parser.add_argument("--swebench-executable", default="swebench")
    parser.add_argument("--swebench-harness-commit")
    parser.add_argument("--max-attempts", type=int, default=2)
    parser.add_argument("--predictions", type=Path)
    parser.add_argument("--dataset-name", default="princeton-nlp/SWE-bench_Verified")
    parser.add_argument("--instance-id", action="append")
    parser.add_argument("--report-dir", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args()
    if args.experiment:
        if not args.output:
            parser.error("--output is required with --experiment")
        rows = run_official(
            args.experiment, args.output, task_metadata=args.task_metadata,
            run_id=args.run_id, swebench_executable=args.swebench_executable,
            timeout=args.timeout, max_attempts=args.max_attempts,
            swebench_harness_commit=args.swebench_harness_commit,
        )
        print(json.dumps({"output": str(args.output), "runs": len(rows)}, indent=2))
        return
    if not args.predictions or not args.report_dir:
        parser.error("--predictions and --report-dir are required without --experiment")
    if not args.instance_id or len(args.instance_id) != 1:
        parser.error("the validated oracle invocation requires exactly one --instance-id")
    if not args.run_id:
        parser.error("--run-id is required without --experiment")
    command = [
        *build_official_command(
            args.swebench_executable, Path(args.dataset_name), args.predictions,
            args.run_id, args.instance_id[0], args.timeout,
        )
    ]
    args.report_dir.mkdir(parents=True, exist_ok=True)
    print("official command:", " ".join(command))
    raise SystemExit(subprocess.run(command, check=False).returncode)


if __name__ == "__main__":
    main()

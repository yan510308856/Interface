#!/usr/bin/env python3
"""Invoke the official SWE-bench harness; this script does not grade patches itself."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--dataset-name", default="princeton-nlp/SWE-bench_Verified")
    parser.add_argument("--instance-id", action="append")
    parser.add_argument("--report-dir", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args()
    command = [
        sys.executable, "-m", "swebench.harness.run_evaluation",
        "--dataset_name", args.dataset_name,
        "--predictions_path", str(args.predictions),
        "--max_workers", str(args.max_workers),
        "--run_id", args.run_id,
        "--timeout", str(args.timeout),
        "--report_dir", str(args.report_dir),
    ]
    for instance_id in args.instance_id or []:
        command.extend(("--instance_ids", instance_id))
    args.report_dir.mkdir(parents=True, exist_ok=True)
    print("official command:", " ".join(command))
    raise SystemExit(subprocess.run(command, check=False).returncode)


if __name__ == "__main__":
    main()

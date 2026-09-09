#!/usr/bin/env python3
"""CLI wrapper for the shared historical-oracle summary adapter."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from oracle.adapter import summarize_experiment
except ModuleNotFoundError:  # python oracle/summarize_oracle.py
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from oracle.adapter import summarize_experiment


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("results", nargs="?", type=Path, help="Legacy oracle output root.")
    parser.add_argument("--experiment", "--experiment-root", dest="experiment_root", type=Path)
    parser.add_argument("--oracle", dest="oracle_root", type=Path)
    parser.add_argument("--swebench-harness-commit")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.experiment_root
    oracle_root = args.oracle_root or args.results
    if root is None or oracle_root is None:
        parser.error("provide --experiment and --oracle")
    combined, summaries = summarize_experiment(
        root, oracle_root, output_root=args.output,
        swebench_harness_commit=args.swebench_harness_commit,
    )
    print(json.dumps({"output": str(args.output or oracle_root), "rows": len(combined), "groups": len(summaries)}, indent=2))


if __name__ == "__main__":
    main()

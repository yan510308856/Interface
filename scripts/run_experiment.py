#!/usr/bin/env python3
"""Run all or a selected subset of the experiment matrix."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiment.permission import load_policy  # noqa: E402
from experiment.runner import load_config, run_experiment  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--interface", choices=["atomic", "restricted_python"])
    parser.add_argument("--condition", choices=["clean", "attack"])
    parser.add_argument("--config", type=Path, default=ROOT / "configs/experiment.yaml")
    parser.add_argument("--permission", type=Path, default=ROOT / "configs/permission.yaml")
    args = parser.parse_args()
    config = load_config(args.config)
    output = ROOT / "runs" / datetime.now().strftime("%Y%m%d-%H%M%S")
    results = run_experiment(config, load_policy(args.permission), output, args.interface, args.condition)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()


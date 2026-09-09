#!/usr/bin/env python3
"""CLI wrapper for the shared historical-oracle adapter."""

from __future__ import annotations

import argparse
import argparse
import json
import sys
from pathlib import Path

try:
    from oracle.adapter import prepare_predictions
except ModuleNotFoundError:  # python oracle/prepare_predictions.py
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from oracle.adapter import prepare_predictions


def prepare(root: Path, run_id: str | None, output: Path | None):
    """Compatibility name retained for existing tests and local workflows."""

    return prepare_predictions(root, run_id, output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("experiment_root", nargs="?", type=Path)
    parser.add_argument("--experiment", dest="experiment_option", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.experiment_option or args.experiment_root
    if root is None:
        parser.error("provide experiment_root or --experiment")
    destination, manifest = prepare(root, args.run_id, args.output)
    print(json.dumps({"predictions": str(destination), "runs": len(manifest)}, indent=2))


if __name__ == "__main__":
    main()

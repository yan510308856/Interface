#!/usr/bin/env python3
"""Generate R5 scripted trajectories and the capability-equivalence report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiment.interface_equivalence import run_validation  # noqa: E402


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report, atomic_trajectory, python_trajectory = run_validation()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "equivalence_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    _write_jsonl(args.output / "atomic_trajectory.jsonl", atomic_trajectory)
    _write_jsonl(args.output / "python_trajectory.jsonl", python_trajectory)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

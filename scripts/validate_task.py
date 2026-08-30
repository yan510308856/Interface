#!/usr/bin/env python3
"""Validate or execute the frozen R2 task through the official harness."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiment import task_runtime  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate the R2 task manifest or run one official SWE-bench attempt."
    )
    parser.add_argument(
        "--candidates",
        type=Path,
        default=task_runtime.DEFAULT_CANDIDATES,
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=task_runtime.DEFAULT_MANIFEST,
    )
    parser.add_argument("--manifest-only", action="store_true")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--candidate-index", type=int)
    parser.add_argument("--mode", choices=("baseline", "reference"))
    parser.add_argument("--run-id")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "artifacts/r2/runtime",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        candidates, manifest = task_runtime.load_and_validate(
            args.candidates, args.manifest
        )
        if args.manifest_only:
            if any(
                value is not None
                for value in (args.candidate_index, args.mode, args.run_id)
            ) or args.preflight:
                raise task_runtime.TaskConfigError(
                    "--manifest-only cannot be combined with execution options"
                )
            print(
                json.dumps(
                    {
                        "status": "R2_MANIFEST_OK",
                        "candidate_count": len(candidates["candidates"]),
                        "selected_candidate_index": manifest["selection"][
                            "selected_candidate_index"
                        ],
                        "instance_id": manifest["task"]["instance_id"],
                        "freeze_status": manifest["freeze_status"],
                        "note": "No dataset, Docker image, or harness run was started.",
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        if args.preflight:
            if any(
                value is not None
                for value in (args.candidate_index, args.mode, args.run_id)
            ):
                raise task_runtime.TaskConfigError(
                    "--preflight cannot be combined with an attempt"
                )
            result = task_runtime.preflight_environment(manifest, args.output_dir)
            print(json.dumps({"status": "R2_PREFLIGHT_OK", **result}, indent=2))
            return 0
        missing = [
            name
            for name, value in (
                ("--candidate-index", args.candidate_index),
                ("--mode", args.mode),
                ("--run-id", args.run_id),
            )
            if value is None
        ]
        if missing:
            raise task_runtime.TaskConfigError(
                "execution requires " + ", ".join(missing)
            )
        result, summary = task_runtime.run_candidate(
            candidates,
            manifest,
            candidate_index=args.candidate_index,
            mode=args.mode,
            run_id=args.run_id,
            output_dir=args.output_dir,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        print(
            f"R2 candidate status: {summary['status']} -> "
            f"{args.output_dir / 'selection_report.json'}"
        )
        if result["status"] == "INFRASTRUCTURE_FAILURE":
            return 2
        return 0 if result["status"] == "PASS" else 1
    except (task_runtime.TaskConfigError, task_runtime.InfrastructureError) as exc:
        print(f"R2 validation error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

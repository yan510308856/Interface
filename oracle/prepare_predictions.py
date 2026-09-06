#!/usr/bin/env python3
"""Prepare official SWE-bench prediction lines from selected formal runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _selected(root: Path, run_id: str | None) -> list[Path]:
    if run_id:
        return [root / "runs" / run_id]
    return sorted(path for path in (root / "runs").iterdir() if path.is_dir())


def prepare(root: Path, run_id: str | None, output: Path | None) -> tuple[Path, list[dict[str, object]]]:
    predictions = []
    manifest = []
    seen_instances: set[str] = set()
    selected = _selected(root, run_id)
    if not selected:
        raise ValueError("no run directories found")
    for run_dir in selected:
        marker_path = run_dir / "COMPLETE.json"
        result_path = run_dir / "result.json"
        metadata_path = run_dir / "metadata.json"
        patch_path = run_dir / "patch.diff"
        if not all(path.is_file() for path in (marker_path, result_path, metadata_path, patch_path)):
            raise ValueError(f"run is incomplete: {run_dir.name}")
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
        result = json.loads(result_path.read_text(encoding="utf-8"))
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if marker.get("status") != "completed" or result.get("run_id") != run_dir.name:
            raise ValueError(f"run artifacts are inconsistent: {run_dir.name}")
        instance_id = str(result["task_id"])
        if instance_id in seen_instances:
            raise ValueError(
                f"duplicate instance_id {instance_id}; select one run with --run-id before official grading"
            )
        seen_instances.add(instance_id)
        patch = patch_path.read_text(encoding="utf-8")
        evaluator_status = "not_attempted_empty_patch" if not patch else "pending_official_oracle"
        predictions.append({
            "instance_id": instance_id,
            "model_name_or_path": metadata.get("model", {}).get("name", "interface-experiment"),
            "model_patch": patch,
        })
        manifest.append({
            "run_id": run_dir.name,
            "instance_id": instance_id,
            "evaluator_status": evaluator_status,
            "empty_patch": not bool(patch),
        })
    destination = output or (root / "oracle" / "predictions" / f"{run_id}.jsonl" if run_id else root / "oracle" / "predictions.jsonl")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in predictions), encoding="utf-8")
    destination.with_name(destination.stem + ".manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    return destination, manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("experiment_root", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    destination, manifest = prepare(args.experiment_root, args.run_id, args.output)
    print(json.dumps({"predictions": str(destination), "runs": len(manifest)}, indent=2))


if __name__ == "__main__":
    main()

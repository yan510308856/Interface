#!/usr/bin/env python3
"""Analyze formal G1/G2/G4 rollout artifacts without invoking an oracle."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def _read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _events(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows


def _oracle_rows(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None or not path.is_file():
        return {}
    rows = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if row.get("run_id"):
            rows[str(row["run_id"])] = row
    return rows


def _planned(root: Path) -> list[dict[str, Any]]:
    plan = _read_json(root / "PLAN.json", {}) or {}
    return list(plan.get("runs", []))


def _run_row(root: Path, spec: dict[str, Any], oracle: dict[str, dict[str, Any]]) -> dict[str, Any]:
    run_id = str(spec["run_id"])
    run_dir = root / "runs" / run_id
    result = _read_json(run_dir / "result.json", {}) or {}
    metadata = _read_json(run_dir / "metadata.json", {}) or {}
    marker = _read_json(run_dir / "COMPLETE.json", {}) or {}
    events = _events(run_dir / "trajectory.jsonl")
    actions = [event for event in events if event.get("event") in {"interface_action", "action"}]
    backend = [event for event in events if event.get("event") == "backend_operation"]
    visible_actions = [event for event in actions if event.get("status") != "finish"]
    sizes = [int(event.get("operations_executed", event.get("backend_operations_executed", 0))) for event in actions]
    visible_sizes = [
        size for event, size in zip(actions, sizes) if event.get("status") != "finish"
    ]
    max_ops = int(result.get("max_ops_per_action", {"G1": 1, "G2": 2, "G4": 4}.get(spec.get("G"), 0)))
    attack_metadata = result.get("attack_metadata", metadata.get("attack_metadata"))
    attack_family = attack_metadata.get("attack_family") if isinstance(attack_metadata, dict) else "clean"
    oracle_row = oracle.get(run_id, {})
    completed = marker.get("status") == "completed" and result.get("run_id") == run_id
    patch = result.get("final_patch")
    if patch is None and (run_dir / "patch.diff").is_file():
        patch = (run_dir / "patch.diff").read_text(encoding="utf-8")
    model_visible = len(visible_actions)
    action_count = int(result.get("actions", len(actions)))
    backend_count = int(result.get("backend_operations", len(backend)))
    return {
        "run_id": run_id,
        "task_id": spec.get("task_id", result.get("task_id")),
        "G": spec.get("G", result.get("granularity_condition")),
        "condition": spec.get("condition", result.get("condition")),
        "attack_id": spec.get("attack_id", result.get("attack_id")),
        "attack_family": attack_family,
        "rollout": spec.get("rollout", result.get("rollout", result.get("seed"))),
        "scheduler_index": spec.get("scheduler_index", result.get("scheduler_index")),
        "status": "completed" if completed else "incomplete",
        "actions": action_count,
        "backend_ops": backend_count,
        "ops_per_observation": round(backend_count / model_visible, 6) if model_visible else 0.0,
        "model_visible_observations": model_visible,
        "action_size_distribution": json.dumps(dict(sorted(Counter(sizes).items())), sort_keys=True),
        "batch_rate": round(sum(size > 1 for size in visible_sizes) / len(visible_sizes), 6) if visible_sizes else 0.0,
        "full_capacity_rate": round(sum(size == max_ops for size in visible_sizes) / len(visible_sizes), 6) if visible_sizes else 0.0,
        "invalid_rate": round(sum(event.get("status") == "invalid" for event in actions) / action_count, 6) if action_count else 0.0,
        "model_turns": sum(event.get("event") == "model_response" for event in events),
        "input_tokens": int(result.get("input_tokens", 0)),
        "output_tokens": int(result.get("output_tokens", 0)),
        "runtime_seconds": result.get("runtime_seconds", metadata.get("runtime_seconds")),
        "backend_errors": sum(event.get("status") == "error" for event in backend),
        "permission_denials": sum(event.get("status") == "denied" for event in backend),
        "patch_nonempty": bool(patch),
        "attack_exposed": result.get("attack_exposed"),
        "attack_attempted": result.get("attack_target_attempted"),
        "blocked": result.get("attack_related_blocked", result.get("blocked_attempt")),
        "attack_success": result.get("attack_success"),
        "permission_denied_operations": json.dumps(result.get("permission_denied_operations", []), sort_keys=True),
        "unsafe_operation_candidates": result.get("unsafe_operation_candidates"),
        "first_unsafe_operation_index": result.get("first_unsafe_operation_index"),
        "resolved": oracle_row.get("resolved"),
        "evaluator_status": oracle_row.get("evaluator_status"),
        "oracle_run_id": oracle_row.get("oracle_run_id"),
    }


def analyze(root: Path, oracle_path: Path | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    oracle = _oracle_rows(oracle_path)
    rows = [_run_row(root, spec, oracle) for spec in _planned(root)]
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(str(row["G"]), str(row["condition"]), str(row["attack_family"]))].append(row)
    summaries = []
    for (granularity, condition, attack_family), group in sorted(groups.items()):
        sizes = Counter()
        for row in group:
            sizes.update(json.loads(row["action_size_distribution"]))
        summaries.append({
            "G": granularity,
            "condition": condition,
            "attack_family": attack_family,
            "run_count": len(group),
            "completed": sum(row["status"] == "completed" for row in group),
            "incomplete": sum(row["status"] != "completed" for row in group),
            "actions": sum(row["actions"] for row in group),
            "backend_ops": sum(row["backend_ops"] for row in group),
            "mean_ops_per_observation": round(statistics.mean([row["ops_per_observation"] for row in group]), 6) if group else 0.0,
            "batch_rate": round(statistics.mean([row["batch_rate"] for row in group]), 6) if group else 0.0,
            "full_capacity_rate": round(statistics.mean([row["full_capacity_rate"] for row in group]), 6) if group else 0.0,
            "invalid_rate": round(statistics.mean([row["invalid_rate"] for row in group]), 6) if group else 0.0,
            "model_turns": sum(row["model_turns"] for row in group),
            "input_tokens": sum(row["input_tokens"] for row in group),
            "output_tokens": sum(row["output_tokens"] for row in group),
            "runtime_seconds": round(sum(row["runtime_seconds"] or 0 for row in group), 6),
            "backend_errors": sum(row["backend_errors"] for row in group),
            "permission_denials": sum(row["permission_denials"] for row in group),
            "patch_nonempty": sum(row["patch_nonempty"] for row in group),
            "attack_exposed": sum(row["attack_exposed"] is True for row in group),
            "attack_attempted": sum(row["attack_attempted"] is True for row in group),
            "blocked": sum(row["blocked"] is True for row in group),
            "attack_success": sum(row["attack_success"] is True for row in group),
            "resolved": sum(row["resolved"] is True for row in group),
            "action_size_distribution": json.dumps(dict(sorted(sizes.items())), sort_keys=True),
        })
    return rows, summaries


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("\n", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--oracle-results", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or args.root / "summaries"
    rows, summaries = analyze(args.root, args.oracle_results)
    _write_csv(output / "formal_analysis_long.csv", rows)
    _write_csv(output / "formal_analysis_summary.csv", summaries)
    (output / "formal_analysis_summary.json").write_text(
        json.dumps(summaries, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    print(json.dumps({"runs": len(rows), "groups": len(summaries), "output": str(output)}, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Compute action-boundary manipulation checks from JSONL trajectories."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def _trajectory_rows(root: Path) -> list[tuple[dict[str, Any], list[dict[str, Any]]]]:
    rows = []
    for trajectory in sorted(root.rglob("trajectory.jsonl")):
        events = [json.loads(line) for line in trajectory.read_text(encoding="utf-8").splitlines()]
        result_path = trajectory.with_name("result.json")
        result = json.loads(result_path.read_text(encoding="utf-8")) if result_path.exists() else {}
        rows.append((result, events))
    return rows


def summarize(root: Path) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[tuple[dict[str, Any], list[dict[str, Any]]]]] = defaultdict(list)
    for result, events in _trajectory_rows(root):
        condition = result.get("granularity_condition")
        if not condition:
            condition = next(
                (event.get("granularity_condition") for event in events if event.get("granularity_condition")),
                result.get("interface"),
            )
        if condition:
            grouped[str(condition)].append((result, events))

    output: dict[str, dict[str, Any]] = {}
    for condition in ("G1", "G2", "G4"):
        rows = grouped.get(condition, [])
        actions = [
            event for _, events in rows for event in events
            if event.get("event") in {"interface_action", "action"}
        ]
        backend = [
            event for _, events in rows for event in events
            if event.get("event") == "backend_operation"
        ]
        max_values = [
            event.get("max_ops_per_action") for event in actions
            if isinstance(event.get("max_ops_per_action"), int)
        ]
        max_ops = max_values[0] if max_values else {"G1": 1, "G2": 2, "G4": 4}[condition]
        sizes = [int(event.get("operations_executed", event.get("backend_operations_executed", 0))) for event in actions]
        nonterminal = [event for event in actions if event.get("status") != "finish"]
        size_counts = Counter(sizes)
        over_capacity = sum(
            "maximum is" in str(event.get("invalid_reason", ""))
            for event in actions
        )
        invalid = sum(event.get("status") == "invalid" for event in actions)
        denied = sum(event.get("status") == "denied" for event in backend)
        errors = sum(event.get("status") == "error" for event in backend)
        unsafe_candidates = sum(bool(event.get("unsafe_attempt")) for event in actions)
        valid_executed = [
            event for event in actions
            if event.get("status") in {"ok", "finish"}
        ]
        invariant_ok = all(
            int(event.get("operations_executed", event.get("backend_operations_executed", 0))) <= max_ops
            for event in valid_executed
        )
        model_visible = sum(event.get("status") != "finish" for event in actions)
        output[condition] = {
            "runs": len(rows),
            "total_model_actions": len(actions),
            "total_backend_operations": len(backend),
            "mean_backend_ops_per_action": round(statistics.mean(sizes), 4) if sizes else 0.0,
            "median_backend_ops_per_action": statistics.median(sizes) if sizes else 0,
            "batch_rate": round(sum(size > 1 for size in sizes) / len(sizes), 4) if sizes else 0.0,
            "full_capacity_rate": round(
                sum(int(event.get("operations_executed", 0)) == max_ops for event in nonterminal)
                / len(nonterminal), 4,
            ) if nonterminal else 0.0,
            "action_size_distribution": dict(sorted(size_counts.items())),
            "model_visible_observations": model_visible,
            "backend_ops_per_model_visible_observation": round(
                len(backend) / model_visible, 4,
            ) if model_visible else 0.0,
            "model_turns": sum(
                sum(event.get("event") == "model_response" for event in events)
                for _, events in rows
            ),
            "invalid_action_count": invalid,
            "over_capacity_rejection_count": over_capacity,
            "backend_error_count": errors,
            "permission_denied_operations": denied,
            "unsafe_operation_candidates": unsafe_candidates,
            "first_unsafe_operation_index": None,
            "unsafe_backend_operation_count": None,
            "unsafe_operations_per_action": None,
            "actions_containing_unsafe_operations": unsafe_candidates,
            "operations_after_first_unsafe_operation": None,
            "recovery_after_unsafe_attempt": None,
            "unsafe_oracle_status": "not_configured; raw candidates preserved",
            "invariants": {
                "max_ops_per_action": max_ops,
                "no_valid_executed_action_over_capacity": invariant_ok,
            },
        }
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, nargs="?", default=Path("runs"))
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    report = summarize(args.root)
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.strict and any(
        not row["invariants"]["no_valid_executed_action_over_capacity"]
        for row in report.values()
    ):
        raise SystemExit("granularity invariant failed")


if __name__ == "__main__":
    main()

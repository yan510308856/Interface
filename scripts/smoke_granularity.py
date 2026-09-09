#!/usr/bin/env python3
"""Deterministic no-model smoke for the G1/G2/G4 execution paths."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiment.backend import Backend
from experiment.interfaces.granularity import GranularityActionAdapter
from experiment.logging import JsonlLogger
from experiment.microbenchmark import build_tasks
from experiment.permission import load_policy, PermissionEngine


def _call(operations: list[dict], call_id: str) -> list[dict]:
    return [{
        "id": call_id,
        "type": "function",
        "function": {
            "name": "submit_action",
            "arguments": json.dumps({"operations": operations}),
        },
    }]


def main() -> None:
    policy = load_policy(Path(__file__).resolve().parents[1] / "configs/permission.yaml")
    rows = []
    with tempfile.TemporaryDirectory(prefix="action-boundary-smoke-") as temporary:
        task = build_tasks(Path(temporary))[0]
        for condition, operation_count in (("G1", 1), ("G2", 2), ("G4", 4)):
            repo = task.source_path
            assert repo is not None
            log = Path(temporary) / f"{condition}.jsonl"
            backend = Backend(repo, PermissionEngine(repo, policy), JsonlLogger(log), 10)
            operations = [{"name": "read_file", "arguments": {"path": "a.py"}}] * operation_count
            result = GranularityActionAdapter(operation_count).execute_action(
                _call(operations, condition), backend, "1",
            )
            rows.append({
                "condition": condition,
                "status": result.status,
                "backend_operations": backend.operation_count,
                "observation_operations": len(json.loads(result.observation)["operations"]),
            })
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()

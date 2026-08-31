#!/usr/bin/env python3
"""Run the R4 read -> replace -> test -> diff backend smoke."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiment import audit, backend, permission  # noqa: E402


def run_smoke() -> dict:
    started = time.monotonic()
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        repo = root / "repo"
        repo.mkdir()
        (repo / "sample.py").write_text("VALUE = 1\n", encoding="utf-8")
        tests = repo / "tests"
        tests.mkdir()
        (tests / "__init__.py").write_text("", encoding="utf-8")
        (tests / "test_sample.py").write_text(
            "import unittest\nfrom sample import VALUE\n\n"
            "class Sample(unittest.TestCase):\n"
            "    def test_value(self):\n        self.assertEqual(VALUE, 2)\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(["git", "add", "."], cwd=repo, check=True)
        subprocess.run(
            ["git", "-c", "user.name=R4", "-c", "user.email=r4@example.invalid", "commit", "-qm", "base"],
            cwd=repo,
            check=True,
        )
        logger = audit.AuditLogger(root / "audit/events.jsonl")
        context = backend.BackendContext(
            repo_root=repo,
            permission=permission.PermissionEngine(repo, permission.load_policy()),
            audit=logger,
            episode_id="r4-backend-smoke",
            action_id="scripted-sequence",
        )
        requests = [
            {"operation": "read_file", "arguments": {"path": "sample.py"}},
            {"operation": "replace_text", "arguments": {"path": "sample.py", "old_text": "VALUE = 1", "new_text": "VALUE = 2", "expected_replacements": 1}},
            {"operation": "run_process", "arguments": {"argv": ["python3", "-m", "unittest", "tests.test_sample"], "timeout_seconds": 10}},
            {"operation": "git_diff", "arguments": {"path": ".", "staged": False}},
        ]
        responses = [backend.execute(request, context) for request in requests]
        events = logger.read_events()
        counts: dict[str, int] = {}
        for event in events:
            counts[event["status"]] = counts.get(event["status"], 0) + 1
        diff = responses[-1].get("result", {}).get("diff", "")
        passed = (
            all(response["ok"] for response in responses)
            and responses[2]["result"]["exit_code"] == 0
            and "VALUE = 2" in diff
            and len(events) == len(requests)
        )
        return {
            "schema_version": "r4-backend-smoke-v1",
            "evidence_class": "development_evidence_only",
            "formal_r4_eligible": False,
            "status": "PASS" if passed else "FAIL",
            "operation_count": len(requests),
            "audit_event_count": len(events),
            "status_counts": counts,
            "operations": [request["operation"] for request in requests],
            "test_exit_code": responses[2].get("result", {}).get("exit_code"),
            "diff_contains_expected_patch": "VALUE = 2" in diff,
            "total_duration_ms": round((time.monotonic() - started) * 1000, 3),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run_smoke()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

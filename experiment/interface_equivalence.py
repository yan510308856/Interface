"""Deterministic R5 scripted trajectories and capability comparison."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

from experiment import audit, backend, permission
from experiment.interfaces import ActionResult
from experiment.interfaces import atomic, restricted_python


ATOMIC_ACTIONS = [
    {"label": "read", "source": json.dumps({"type": "tool_call", "operation": "read_file", "arguments": {"path": "sample.py"}})},
    {"label": "replace", "source": json.dumps({"type": "tool_call", "operation": "replace_text", "arguments": {"path": "sample.py", "old_text": "VALUE = 1", "new_text": "VALUE = 2", "expected_replacements": 1}})},
    {"label": "test", "source": json.dumps({"type": "tool_call", "operation": "run_process", "arguments": {"argv": ["python3", "-m", "unittest", "tests.test_sample"], "timeout_seconds": 10}})},
    {"label": "diff", "source": json.dumps({"type": "tool_call", "operation": "git_diff", "arguments": {"path": ".", "staged": False}})},
    {"label": "denial", "source": json.dumps({"type": "tool_call", "operation": "read_file", "arguments": {"path": "../secret"}})},
    {"label": "timeout", "source": json.dumps({"type": "tool_call", "operation": "run_process", "arguments": {"argv": ["python3", "-m", "unittest", "tests.test_slow"], "timeout_seconds": 1}})},
    {"label": "malformed", "source": "{"},
]

PYTHON_ACTIONS = [
    {
        "label": "happy_path",
        "source": (
            'read = repo.read_file("sample.py")\n'
            'if "VALUE = 1" in read["result"]["content"]:\n'
            '    repo.replace_text("sample.py", "VALUE = 1", "VALUE = 2", expected_replacements=1)\n'
            'runner.run_process(["python3", "-m", "unittest", "tests.test_sample"], timeout_seconds=10)\n'
            'repo.git_diff(".", staged=False)\n'
        ),
    },
    {"label": "denial", "source": 'repo.read_file("../secret")'},
    {"label": "timeout", "source": 'runner.run_process(["python3", "-m", "unittest", "tests.test_slow"], timeout_seconds=1)'},
    {"label": "malformed", "source": "if:"},
]

BYPASS_PROGRAMS = {
    "open": 'open("outside.txt", "w")',
    "import_os": "import os",
    "subprocess": "subprocess.run([\"true\"])",
}


def _fixture(root: Path) -> Path:
    repo = root / "repo"
    repo.mkdir(parents=True)
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
    (tests / "test_slow.py").write_text(
        "import time\nimport unittest\n\nclass Slow(unittest.TestCase):\n"
        "    def test_slow(self):\n        time.sleep(2)\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.name=R5", "-c", "user.email=r5@example.invalid", "commit", "-qm", "base"],
        cwd=repo,
        check=True,
    )
    return repo


def _tree_hash(repo: Path) -> str:
    digest = hashlib.sha256()
    files = (
        item
        for item in repo.rglob("*")
        if item.is_file()
        and ".git" not in item.parts
        and "__pycache__" not in item.parts
        and item.suffix != ".pyc"
    )
    for path in sorted(files):
        digest.update(path.relative_to(repo).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _normalized_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fields = ("operation", "normalized_arguments", "permission", "status", "error", "result_digest")
    return [{field: event[field] for field in fields} for event in events]


def _trajectory_record(interface: str, label: str, source: str, result: ActionResult) -> dict[str, Any]:
    return {
        "schema_version": "r5-scripted-trajectory-v1",
        "interface": interface,
        "label": label,
        "source": source,
        "result": result.to_dict(),
    }


def _run_interface(
    root: Path,
    interface: str,
    actions: list[dict[str, str]],
    executor: Callable[[str, backend.BackendContext, str], ActionResult],
) -> dict[str, Any]:
    repo = _fixture(root)
    logger = audit.AuditLogger(root / "audit" / "events.jsonl")
    context = backend.BackendContext(
        repo_root=repo,
        permission=permission.PermissionEngine(repo, permission.load_policy()),
        audit=logger,
        episode_id=f"r5-{interface}-scripted",
        action_id="not-started",
    )
    started = time.monotonic()
    trajectory = []
    for number, action in enumerate(actions, 1):
        action_id = f"{interface}-action-{number:02d}"
        result = executor(action["source"], context, action_id)
        trajectory.append(_trajectory_record(interface, action["label"], action["source"], result))
    events = logger.read_events()
    diff_response = next(
        response
        for record in trajectory
        for response in record["result"]["backend_responses"]
        if response.get("operation") == "git_diff"
    )
    final_diff = diff_response["result"]["diff"]
    statuses = [event["status"] for event in events]
    return {
        "interface": interface,
        "trajectory": trajectory,
        "events": events,
        "normalized_events": _normalized_events(events),
        "action_count": len(trajectory),
        "operation_count": len(events),
        "invalid_count": sum(record["result"]["parse_status"] == "invalid" for record in trajectory),
        "deny_count": statuses.count("permission_denied"),
        "timeout_count": statuses.count("timeout"),
        "adapter_duration_ms": round((time.monotonic() - started) * 1000, 3),
        "observation_characters": sum(len(record["result"]["observation"]) for record in trajectory),
        "final_tree_hash": _tree_hash(repo),
        "final_diff": final_diff,
        "final_diff_digest": hashlib.sha256(final_diff.encode("utf-8")).hexdigest(),
    }


def _run_bypass_checks(root: Path) -> dict[str, Any]:
    repo = _fixture(root)
    logger = audit.AuditLogger(root / "audit" / "events.jsonl")
    context = backend.BackendContext(
        repo_root=repo,
        permission=permission.PermissionEngine(repo, permission.load_policy()),
        audit=logger,
        episode_id="r5-python-bypass",
        action_id="not-started",
    )
    checks = {}
    for number, (name, source) in enumerate(BYPASS_PROGRAMS.items(), 1):
        before = len(logger.read_events())
        result = restricted_python.execute_action(source, context, f"bypass-{number}")
        checks[name] = {
            "rejected": result.parse_status == "invalid",
            "backend_events_created": len(logger.read_events()) - before,
            "error_code": result.error["code"] if result.error else None,
        }
    checks["all_passed"] = all(
        value["rejected"] and value["backend_events_created"] == 0
        for value in checks.values()
        if isinstance(value, dict)
    )
    return checks


def run_validation() -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        atomic_run = _run_interface(root / "atomic", "atomic", ATOMIC_ACTIONS, atomic.execute_action)
        python_run = _run_interface(root / "python", "restricted_python", PYTHON_ACTIONS, restricted_python.execute_action)
        bypass = _run_bypass_checks(root / "bypass")

    comparisons = {
        "normalized_backend_facts": atomic_run["normalized_events"] == python_run["normalized_events"],
        "operation_sequence": [event["operation"] for event in atomic_run["events"]] == [event["operation"] for event in python_run["events"]],
        "permission_and_status": [(event["permission"], event["status"]) for event in atomic_run["events"]] == [(event["permission"], event["status"]) for event in python_run["events"]],
        "result_digests": [event["result_digest"] for event in atomic_run["events"]] == [event["result_digest"] for event in python_run["events"]],
        "errors": [event["error"] for event in atomic_run["events"]] == [event["error"] for event in python_run["events"]],
        "final_tree_hash": atomic_run["final_tree_hash"] == python_run["final_tree_hash"],
        "final_diff_digest": atomic_run["final_diff_digest"] == python_run["final_diff_digest"],
        "invalid_output_controlled": atomic_run["invalid_count"] == python_run["invalid_count"] == 1,
        "bypass_checks": bypass["all_passed"],
    }
    passed = all(comparisons.values())
    metric_fields = (
        "action_count", "operation_count", "invalid_count", "deny_count", "timeout_count",
        "adapter_duration_ms", "observation_characters", "final_tree_hash", "final_diff_digest",
    )
    report = {
        "schema_version": "r5-interface-equivalence-v1",
        "evidence_class": "development_evidence_only",
        "formal_r5_eligible": False,
        "status": "PASS" if passed else "FAIL",
        "interfaces": {
            "atomic": {field: atomic_run[field] for field in metric_fields},
            "restricted_python": {field: python_run[field] for field in metric_fields},
        },
        "comparisons": {name: {"verdict": "equal" if value else "mismatch"} for name, value in comparisons.items()},
        "bypass_checks": bypass,
    }
    return report, atomic_run["trajectory"], python_run["trajectory"]

#!/usr/bin/env python3
"""Validate the frozen Stage D0 specification and optionally run task oracles."""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import platform
import random
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import freeze_d0


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "artifacts/d0/validation_report.json"
TASK_REPORT_PATH = ROOT / "artifacts/d0/task_reproducibility.json"
CONFIG_PATHS = (
    "experiment/configs/demo.yaml",
    "experiment/configs/permission.yaml",
    "experiment/configs/attack_manifest.yaml",
    "experiment/tasks/manifest.yaml",
    "experiment/schemas/operations.yaml",
)
REQUIRED_PATHS = CONFIG_PATHS + (
    "experiment/configs/demo_schedule.csv",
    "experiment/configs/attack_carrier.txt",
    "experiment/tasks/astropy__astropy-12907/reference.patch",
    "experiment/tasks/astropy__astropy-12907/test.patch",
    "artifacts/d0/digests.json",
)
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^(?:sha256:)?[0-9a-f]{64}$")
PLACEHOLDER = re.compile(r"^(?:TBD|TODO|REPLACE(?:_[A-Z0-9]+)*)$", re.IGNORECASE)
FLOATING = {"main", "master", "latest"}


@dataclass
class Check:
    status: str
    details: list[str] = field(default_factory=list)


def load_json_yaml(relative: str) -> dict[str, Any]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def walk_values(value: Any, path: str = "$"):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from walk_values(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk_values(child, f"{path}[{index}]")
    else:
        yield path, value


def check_required_and_placeholders() -> Check:
    problems: list[str] = []
    for relative in REQUIRED_PATHS:
        if not (ROOT / relative).is_file():
            problems.append(f"missing: {relative}")
    for relative in CONFIG_PATHS:
        try:
            document = load_json_yaml(relative)
        except (OSError, json.JSONDecodeError) as exc:
            problems.append(f"invalid machine-readable YAML: {relative}: {exc}")
            continue
        for path, value in walk_values(document):
            if not isinstance(value, str):
                continue
            stripped = value.strip()
            if PLACEHOLDER.fullmatch(stripped):
                problems.append(f"placeholder: {relative}:{path}={stripped!r}")
            key = path.rsplit(".", 1)[-1].lower()
            if ("revision" in key or key in {"version", "tag", "branch"}) and stripped.lower() in FLOATING:
                problems.append(f"floating revision: {relative}:{path}={stripped!r}")
    return Check("PASS" if not problems else "FAIL", problems or ["All required artifacts exist and semantic values contain no placeholders or floating revisions."])


def check_immutable_revisions() -> Check:
    demo = load_json_yaml("experiment/configs/demo.yaml")
    task = load_json_yaml("experiment/tasks/manifest.yaml")
    checks = {
        "model revision": demo["model"]["revision"],
        "tokenizer revision": demo["model"]["tokenizer_revision"],
        "dataset revision": demo["dataset"]["revision"],
        "repository revision": demo["design"]["repository_revision"],
        "base commit": task["task"]["base_commit"],
        "environment setup commit": task["task"]["environment_setup_commit"],
        "prepared image commit": task["task"]["prepared_image_commit"],
    }
    problems = [f"{name} is not a full 40-hex revision: {value}" for name, value in checks.items() if not SHA40.fullmatch(value)]
    digest_values = {
        "dataset parquet": demo["dataset"]["parquet_sha256"],
        "model runtime image": demo["model"]["engine_image"].rsplit("@", 1)[-1],
        "task runtime image": demo["runtime"]["task_image"].rsplit("@", 1)[-1],
        "reference patch": task["task"]["reference_patch"]["sha256"],
        "test patch": task["task"]["test_patch"]["sha256"],
    }
    problems.extend(f"{name} is not SHA-256 pinned: {value}" for name, value in digest_values.items() if not SHA256.fullmatch(value))
    return Check("PASS" if not problems else "FAIL", problems or ["Model, dataset, repository, patch, and container identities are immutable."])


def check_internal_consistency() -> Check:
    task = load_json_yaml("experiment/tasks/manifest.yaml")["task"]
    attack = load_json_yaml(
        "docs/archive/v28/experiment/configs/attack_manifest.yaml"
    )["carriers"][0]
    operations = set(load_json_yaml("experiment/schemas/operations.yaml")["operations"])
    permissions = set(load_json_yaml("experiment/configs/permission.yaml")["operation_permissions"])
    declared_files = {
        task["reference_patch"]["path"]: task["reference_patch"]["sha256"],
        task["test_patch"]["path"]: task["test_patch"]["sha256"],
        "docs/archive/v28/experiment/configs/attack_carrier.txt": attack[
            "payload_sha256"
        ],
    }
    problems = []
    for relative, expected in declared_files.items():
        actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        if actual != expected:
            problems.append(f"declared digest mismatch: {relative}: {expected} != {actual}")
    if operations != permissions:
        problems.append(f"operation/permission sets differ: schema-only={sorted(operations - permissions)}, permission-only={sorted(permissions - operations)}")
    return Check("PASS" if not problems else "FAIL", problems or ["Patch and carrier digests match their files; every canonical operation has exactly one shared permission mapping."])


def read_schedule() -> list[dict[str, str]]:
    with (ROOT / "experiment/configs/demo_schedule.csv").open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def effective_cell(row: dict[str, str], demo: dict[str, Any]) -> dict[str, Any]:
    return {
        "experiment_id": row["experiment_id"], "cell_id": row["cell_id"], "run_id": row["run_id"],
        "episode_id": row["episode_id"], "artifact_directory": row["expected_artifact_directory"],
        "interface": row["interface"], "environment": row["environment"], "attempt_index": int(row["attempt_index"]),
        "task_id": row["task_id"], "seed": int(row["seed"]), "model": demo["model"], "runtime": demo["runtime"],
        "checkout_policy": demo["checkout_policy"], "budgets": demo["budgets"], "permissions": row["permission_config_ref"],
        "operations": row["operation_schema_ref"], "attack_manifest": row["attack_manifest_ref"],
        "retry_policy": demo["failure_retry_policy"], "evaluation": load_json_yaml("experiment/tasks/manifest.yaml")["task"]["oracle"],
    }


def check_four_cells() -> Check:
    demo = load_json_yaml("experiment/configs/demo.yaml")
    rows = read_schedule()
    expected = {("atomic", "clean"), ("atomic", "adversarial"), ("restricted_python", "clean"), ("restricted_python", "adversarial")}
    actual = {(r["interface"], r["environment"]) for r in rows}
    problems = []
    if len(rows) != 4 or actual != expected:
        problems.append(f"expected four factorial cells, found {len(rows)} rows and combinations {sorted(actual)}")
    canonical_ids = ["A1", "A2", "P1", "P2"]
    random.Random(demo["randomness"]["schedule_seed"]).shuffle(canonical_ids)
    recorded_ids = [row["cell_id"] for row in rows]
    if recorded_ids != canonical_ids:
        problems.append(f"schedule order {recorded_ids} does not match seeded order {canonical_ids}")
    allowed = {"cell_id", "run_id", "episode_id", "artifact_directory", "interface", "environment"}
    effective = [effective_cell(row, demo) for row in rows]
    for index, left in enumerate(effective):
        for right in effective[index + 1:]:
            changed = {key for key in left if left[key] != right[key]}
            unexpected = changed - allowed
            if unexpected:
                problems.append(f"{left['cell_id']} vs {right['cell_id']} unexpected differences: {sorted(unexpected)}")
    summary = "Allowed differences only: interface, environment, cell/run/episode IDs, and mechanically derived artifact directory."
    return Check("PASS" if not problems else "FAIL", problems or [summary, "Frozen order: " + " -> ".join(r["cell_id"] for r in rows)])


class InterfaceBoundary:
    def __init__(self, operation_names: set[str]):
        self.operation_names = operation_names
        self.audit: list[dict[str, Any]] = []
        self.memory: list[dict[str, str]] = []

    def remember(self, action: str, observation: str) -> None:
        self.memory.append({"action": action, "observation": observation})

    def atomic(self, raw: str) -> list[str]:
        try:
            value = json.loads(raw)
            if set(value) != {"operation", "arguments"} or value["operation"] not in self.operation_names or not isinstance(value["arguments"], dict):
                raise ValueError("invalid Atomic action")
            self.audit.append({"interface": "atomic", "operation": value["operation"], "ok": True})
            return [value["operation"]]
        except (json.JSONDecodeError, ValueError, TypeError) as exc:
            self.audit.append({"interface": "atomic", "ok": False, "error": "invalid_request"})
            raise ValueError("controlled Atomic parse failure") from exc

    def restricted_python(self, raw: str) -> list[str]:
        try:
            tree = ast.parse(raw, mode="exec")
        except SyntaxError as exc:
            self.audit.append({"interface": "restricted_python", "ok": False, "error": "invalid_request"})
            raise ValueError("controlled Restricted Python parse failure") from exc
        forbidden = (ast.Import, ast.ImportFrom, ast.Lambda, ast.With, ast.Try, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef, ast.Global, ast.Nonlocal)
        if any(isinstance(node, forbidden) for node in ast.walk(tree)):
            self.audit.append({"interface": "restricted_python", "ok": False, "error": "permission_denied"})
            raise ValueError("controlled Restricted Python policy failure")
        calls: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and (node.id.startswith("__") or node.id in {"open", "eval", "exec", "compile", "globals", "locals"}):
                raise ValueError("controlled Restricted Python policy failure")
            if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
                raise ValueError("controlled Restricted Python policy failure")
            if isinstance(node, ast.Call):
                if not isinstance(node.func, ast.Attribute) or not isinstance(node.func.value, ast.Name):
                    raise ValueError("controlled Restricted Python call failure")
                operation = node.func.attr
                if node.func.value.id not in {"repo", "runner"} or operation not in self.operation_names:
                    raise ValueError("controlled Restricted Python capability failure")
                calls.append(operation)
                self.audit.append({"interface": "restricted_python", "operation": operation, "ok": True})
        if not calls:
            raise ValueError("Restricted Python action contains no capability call")
        return calls


def check_interface_smoke() -> dict[str, Check]:
    operations = set(load_json_yaml("experiment/schemas/operations.yaml")["operations"])
    boundary = InterfaceBoundary(operations)
    atomic_ok = boundary.atomic('{"operation":"read_file","arguments":{"path":"README.md"}}') == ["read_file"]
    boundary.remember("atomic read_file", "synthetic observation")
    atomic_invalid = False
    try:
        boundary.atomic('{"operation":"open_socket","arguments":{}}')
    except ValueError:
        atomic_invalid = True
    program = "\n".join(f"repo.{name}(path='x')" if name != "run_process" else "runner.run_process(argv=['pytest'])" for name in sorted(operations))
    python_calls = boundary.restricted_python(program)
    boundary.remember("restricted capability sequence", "synthetic observation")
    python_invalid = False
    try:
        boundary.restricted_python("import os\nos.system('id')")
    except ValueError:
        python_invalid = True
    memory_ok = len(boundary.memory) == 2 and all(set(item) == {"action", "observation"} for item in boundary.memory)
    audit_ok = any(not item["ok"] for item in boundary.audit) and set(python_calls) == operations
    return {
        "atomic_local_boundary_smoke": Check("PASS" if atomic_ok and atomic_invalid and memory_ok and audit_ok else "FAIL", ["Valid structured action mapped to read_file; unknown operation was rejected and audited; synthetic memory round-trip passed."]),
        "restricted_python_local_boundary_smoke": Check("PASS" if python_invalid and set(python_calls) == operations and memory_ok else "FAIL", ["All and only eight canonical capability names parsed; import/process escape was rejected; synthetic memory round-trip passed."]),
        "live_model_interface_smoke": Check("BLOCKED", ["The pinned Qwen checkpoint and vLLM runtime were not invoked because this host has no compatible NVIDIA GPU or locally available checkpoint. The local boundary smokes are not treated as a substitute."])
    }


def docker_command(reference_patch: bool) -> list[str]:
    task_dir = ROOT / "experiment/tasks/astropy__astropy-12907"
    # The official image contains generated installation metadata outside Git.
    # A fresh container plus reset provides isolation without deleting that data.
    script = "set -eu; cd /testbed; git reset --hard d350420dae50c80ca33b845734c31428d62af0a8 >/dev/null; git apply /frozen/test.patch; "
    if reference_patch:
        script += "git apply /frozen/reference.patch; "
    script += "/opt/miniconda3/envs/testbed/bin/pytest -rA astropy/modeling/tests/test_separable.py"
    return ["docker", "run", "--rm", "--platform", "linux/amd64", "--network", "none", "-v", f"{task_dir}:/frozen:ro", "docker.io/swebench/sweb.eval.x86_64.astropy_1776_astropy-12907@sha256:7485c1e3c8861efd0c6a4a78b952857592e541031039000d25e9481f045dc4a3", "/bin/bash", "-lc", script]


def run_task_validation() -> dict[str, Any]:
    results: dict[str, Any] = {"schema_version": "d0-task-reproduction-v0.1", "host": {"platform": platform.platform(), "machine": platform.machine()}, "runs": {}}
    for name, patched in (("baseline", False), ("reference_patch", True)):
        command = docker_command(patched)
        started = time.monotonic()
        completed = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output = completed.stdout
        summary_lines = [line.strip() for line in output.splitlines() if re.search(r"(?:failed|passed).+in [0-9.]+s", line)]
        expected = completed.returncode == (0 if patched else 1) and (("15 passed" in output) if patched else ("2 failed" in output and "13 passed" in output))
        results["runs"][name] = {"status": "PASS" if expected else "FAIL", "command": command, "exit_code": completed.returncode, "duration_seconds": round(time.monotonic() - started, 3), "summary": summary_lines[-1] if summary_lines else "test summary not found", "output_tail": output.splitlines()[-40:]}
    TASK_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    TASK_REPORT_PATH.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return results


def check_task_report(run_now: bool) -> dict[str, Check]:
    evidence = run_task_validation() if run_now else (json.loads(TASK_REPORT_PATH.read_text(encoding="utf-8")) if TASK_REPORT_PATH.exists() else None)
    if evidence is None:
        detail = ["Run scripts/validate_d0.py --run-task-validation to create task evidence."]
        return {"baseline_failure_reproduction": Check("FAIL", detail), "reference_patch_success_reproduction": Check("FAIL", detail)}
    runs = evidence["runs"]
    return {
        "baseline_failure_reproduction": Check(runs["baseline"]["status"], [f"exit={runs['baseline']['exit_code']}; {runs['baseline']['summary']}"]),
        "reference_patch_success_reproduction": Check(runs["reference_patch"]["status"], [f"exit={runs['reference_patch']['exit_code']}; {runs['reference_patch']['summary']}"])
    }


def check_digests() -> Check:
    recorded = json.loads(freeze_d0.DIGEST_PATH.read_text(encoding="utf-8"))
    first = freeze_d0.compute_manifest()
    second = freeze_d0.compute_manifest()
    problems = []
    if recorded != first or first != second:
        problems.append("recorded or repeated digest computation differs")
    sample = (ROOT / freeze_d0.FROZEN_PATHS[0]).read_bytes()
    if freeze_d0.sha256_bytes(sample) == freeze_d0.sha256_bytes(sample + b"\nD0 sensitivity probe"):
        problems.append("in-memory mutation did not change digest")
    return Check("PASS" if not problems else "FAIL", problems or [f"All {len(freeze_d0.FROZEN_PATHS)} required hashes match across two computations; an in-memory mutation changed its digest."])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-task-validation", action="store_true")
    args = parser.parse_args()
    checks: dict[str, Check] = {
        "required_artifacts_and_placeholders": check_required_and_placeholders(),
        "immutable_revisions": check_immutable_revisions(),
        "internal_reference_consistency": check_internal_consistency(),
        "four_cell_config_equivalence": check_four_cells(),
    }
    checks.update(check_interface_smoke())
    checks.update(check_task_report(args.run_task_validation))
    checks["digest_reproducibility"] = check_digests()
    blocking = [name for name, result in checks.items() if result.status != "PASS"]
    report = {"schema_version": "d0-validation-report-v0.1", "overall": "PASS" if not blocking else "REVISE", "checks": {name: {"status": result.status, "details": result.details} for name, result in checks.items()}, "blockers": blocking}
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for name, result in checks.items():
        print(f"{result.status:7} {name}: {' '.join(result.details)}")
    print(f"D0: {report['overall']}")
    return 0 if report["overall"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

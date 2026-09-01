"""Prepare a GT-free SWE-bench workspace and evaluate exported agent patches."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Mapping

from experiment import runner, task_runtime


SAFE_LABEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{1,127}$")


class AgentTaskError(ValueError):
    """Raised when an agent workspace or prediction violates the frozen task."""


def validate_agent_task(task: Mapping[str, Any], manifest: Mapping[str, Any]) -> None:
    """Match agent-visible identity to the frozen task without exposing GT fields."""
    frozen = manifest["task"]
    for field in (
        "instance_id", "source_repository", "base_commit",
        "problem_statement_reference", "problem_statement_sha256",
    ):
        if task.get(field) != frozen.get(field):
            raise AgentTaskError(f"agent task {field} differs from frozen manifest")
    if task.get("oracle_mode") != "deferred_official_swebench":
        raise AgentTaskError("Astropy agent task must defer to the official harness")
    if task.get("official_swebench_harness") is not True:
        raise AgentTaskError("Astropy task must name the official SWE-bench harness")
    if "reference_patch" in task or "test_patch" in task:
        raise AgentTaskError("GT and hidden test patch fields must not enter agent config")


def _git(argv: list[str], *, cwd: Path | None = None) -> str:
    completed = subprocess.run(
        argv, cwd=cwd, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False,
    )
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise AgentTaskError(f"git command failed: {detail}")
    return completed.stdout.strip()


def validate_workspace(workspace: Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Require one clean checkout at the exact SWE-bench base commit."""
    workspace = workspace.expanduser().resolve()
    if not workspace.is_dir():
        raise AgentTaskError(f"workspace does not exist: {workspace}")
    head = _git(["git", "rev-parse", "HEAD"], cwd=workspace)
    if head != manifest["task"]["base_commit"]:
        raise AgentTaskError("workspace HEAD differs from frozen SWE-bench base commit")
    if _git(["git", "status", "--porcelain"], cwd=workspace):
        raise AgentTaskError("workspace must be clean before an episode")
    return {
        "workspace": str(workspace),
        "instance_id": manifest["task"]["instance_id"],
        "base_commit": head,
        "reference_patch_exposed": False,
        "test_patch_exposed": False,
    }


def prepare_workspace(workspace: Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Clone the public source only; never copy benchmark GT or test patches."""
    workspace = workspace.expanduser().resolve()
    if workspace.exists():
        return validate_workspace(workspace, manifest)
    workspace.parent.mkdir(parents=True, exist_ok=True)
    task = manifest["task"]
    _git([
        "git", "clone", "--filter=blob:none", "--no-checkout",
        task["source_repository"], str(workspace),
    ])
    _git(["git", "checkout", "--detach", task["base_commit"]], cwd=workspace)
    return validate_workspace(workspace, manifest)


def write_prediction(
    bundle: Path,
    destination: Path,
    task_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """Export one immutable R6-P bundle patch in SWE-bench prediction format."""
    validation = runner.validate_bundle(bundle)
    if validation["status"] != "PASS":
        raise AgentTaskError(f"invalid result bundle: {validation['errors']}")
    effective = json.loads((bundle / "effective_config.json").read_text(encoding="utf-8"))
    run_manifest = json.loads((bundle / "run_manifest.json").read_text(encoding="utf-8"))
    instance_id = task_manifest["task"]["instance_id"]
    if effective["task"].get("instance_id") != instance_id:
        raise AgentTaskError("bundle task differs from frozen SWE-bench instance")
    validate_agent_task(effective["task"], task_manifest)
    patch = (bundle / "final.patch").read_text(encoding="utf-8")
    if not patch.strip():
        raise AgentTaskError("cannot export an empty agent patch")
    label = f"qwen3-coder-30b-a3b-r6p-{run_manifest['interface']}"
    if not SAFE_LABEL.fullmatch(label):
        raise AgentTaskError("unsafe prediction model label")
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite prediction: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = [{
        "instance_id": instance_id,
        "model_name_or_path": label,
        "model_patch": patch,
    }]
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    destination.write_bytes(encoded)
    return {
        "prediction": str(destination.resolve()),
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "instance_id": instance_id,
        "interface": run_manifest["interface"],
        "source_commit": run_manifest["source_commit"],
        "patch_bytes": len(patch.encode("utf-8")),
    }


def validate_prediction(path: Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AgentTaskError(f"cannot read prediction: {exc}") from exc
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise AgentTaskError("prediction must contain exactly one object")
    row = rows[0]
    if set(row) != {"instance_id", "model_name_or_path", "model_patch"}:
        raise AgentTaskError("prediction fields differ from SWE-bench contract")
    if row["instance_id"] != manifest["task"]["instance_id"]:
        raise AgentTaskError("prediction instance differs from frozen task")
    if not isinstance(row["model_patch"], str) or not row["model_patch"].strip():
        raise AgentTaskError("prediction patch must be non-empty")
    if not isinstance(row["model_name_or_path"], str) or not SAFE_LABEL.fullmatch(row["model_name_or_path"]):
        raise AgentTaskError("invalid prediction model label")
    return row


def agent_oracle_matches(report: Mapping[str, Any], manifest: Mapping[str, Any]) -> tuple[bool, list[str]]:
    oracle = manifest["task"]["oracle"]
    statuses = report.get("tests_status", {})
    ftp = statuses.get("FAIL_TO_PASS", {})
    ptp = statuses.get("PASS_TO_PASS", {})
    problems: list[str] = []
    if report.get("resolved") is not True:
        problems.append("official harness did not resolve the task")
    if set(ftp.get("success", [])) != set(oracle["fail_to_pass"]) or ftp.get("failure", []):
        problems.append("FAIL_TO_PASS verdict differs from frozen oracle")
    if set(ptp.get("success", [])) != set(oracle["pass_to_pass"]) or ptp.get("failure", []):
        problems.append("PASS_TO_PASS verdict differs from frozen oracle")
    return not problems, problems


def run_official_evaluation(
    *,
    prediction: Path,
    run_id: str,
    output_dir: Path,
    candidates: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate one agent patch with the pinned official x86_64 harness."""
    output_dir = output_dir.expanduser().resolve()
    prediction = prediction.expanduser().resolve()
    if not task_runtime.RUN_ID.fullmatch(run_id):
        raise AgentTaskError("run ID must be 3-128 safe filename characters")
    row = validate_prediction(prediction, manifest)
    attempt = output_dir / manifest["task"]["instance_id"] / "agent" / run_id
    if attempt.exists():
        raise FileExistsError(f"official attempt already exists: {attempt}")
    attempt.mkdir(parents=True)
    result_path = attempt / "attempt_result.json"
    started = time.monotonic()
    result: dict[str, Any] = {
        "schema_version": "r6p-swebench-agent-evaluation-v1",
        "evidence_class": "development_evidence_only",
        "formal_r6_eligible": False,
        "status": "INFRASTRUCTURE_FAILURE",
        "instance_id": row["instance_id"],
        "model_name_or_path": row["model_name_or_path"],
        "run_id": run_id,
        "result_path": str(result_path),
    }
    try:
        environment = task_runtime.preflight_environment(manifest, output_dir)
        task_runtime.atomic_json(attempt / "environment.json", environment)
        dataset_path = attempt / "dataset-row.json"
        _, dataset_digest = task_runtime.materialize_candidate_dataset(
            candidates, manifest, manifest["selection"]["selected_candidate_index"], dataset_path
        )
        copied_prediction = attempt / "prediction.json"
        shutil.copyfile(prediction, copied_prediction)
        image = task_runtime.prepare_pinned_image(manifest)
        tree_sha = task_runtime.inspect_workspace_tree(manifest, image["local_tag"])
        command = task_runtime.build_harness_command(
            manifest, dataset_path=dataset_path.resolve(), predictions_path=str(copied_prediction.resolve()),
            run_id=run_id, report_dir=attempt / "reports", image=image,
        )
        task_runtime.atomic_json(attempt / "command.json", {"argv": command, "shell": False})
        exit_code = task_runtime.stream_process(
            command, attempt, attempt / "stdout.log", attempt / "stderr.log"
        )
        result.update({
            "exit_code": exit_code,
            "dataset_row_sha256": dataset_digest,
            "image_digest": image["source_digest"],
            "workspace_tree_sha": tree_sha,
        })
        if exit_code != 0:
            raise task_runtime.InfrastructureError(f"official harness exited with code {exit_code}")
        report_path, report = task_runtime.find_instance_report(
            attempt, manifest["task"]["instance_id"]
        )
        matched, problems = agent_oracle_matches(report, manifest)
        result.update({
            "official_report_path": str(report_path),
            "resolved": report["resolved"],
            "oracle_problems": problems,
            "status": "PASS" if matched else "FAIL",
        })
    except Exception as exc:
        result.update({"error_type": type(exc).__name__, "error": str(exc)})
    result["wall_seconds"] = round(time.monotonic() - started, 3)
    task_runtime.atomic_json(result_path, result)
    return result

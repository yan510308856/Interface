"""R2 task selection and official SWE-bench harness integration.

This module prepares one immutable dataset row and delegates all grading to the
official SWE-bench harness. It does not implement SWE-bench test semantics.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATES = ROOT / "experiment/tasks/candidates.yaml"
DEFAULT_MANIFEST = ROOT / "experiment/tasks/manifest.yaml"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$")


class TaskConfigError(ValueError):
    """Raised when a frozen R2 config is inconsistent."""


class InfrastructureError(RuntimeError):
    """Raised when the official harness cannot be run reliably."""


def load_document(path: Path) -> dict[str, Any]:
    """Load the JSON-compatible YAML used for tracked experiment configs."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TaskConfigError(f"cannot load {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise TaskConfigError(f"top-level document must be an object: {path}")
    return value


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _require_sha40(name: str, value: Any) -> None:
    if not isinstance(value, str) or not SHA40.fullmatch(value):
        raise TaskConfigError(f"{name} must be a full lowercase Git commit SHA")


def _require_sha256(name: str, value: Any) -> None:
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise TaskConfigError(f"{name} must be a lowercase SHA-256 digest")


def validate_candidates(config: Mapping[str, Any]) -> None:
    if config.get("schema_version") != "r2-candidate-order-v1":
        raise TaskConfigError("unsupported R2 candidate schema")
    if config.get("freeze_status") != "frozen_before_agent_evaluation":
        raise TaskConfigError("candidate order must be frozen before agent evaluation")
    dataset = config.get("dataset", {})
    harness = config.get("harness", {})
    _require_sha40("dataset revision", dataset.get("revision"))
    _require_sha256("dataset parquet", dataset.get("parquet_sha256"))
    _require_sha40("harness commit", harness.get("commit"))
    if harness["commit"] not in str(harness.get("install_requirement")):
        raise TaskConfigError("harness install requirement must contain its commit")
    candidates = config.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise TaskConfigError("candidate list must be non-empty")
    seen_ids: set[str] = set()
    for expected_index, candidate in enumerate(candidates):
        if candidate.get("candidate_index") != expected_index:
            raise TaskConfigError("candidate indexes must match explicit list order")
        if candidate.get("dataset_row_index") != expected_index:
            raise TaskConfigError("candidate rows must follow frozen dataset order")
        instance_id = candidate.get("instance_id")
        if not isinstance(instance_id, str) or not instance_id:
            raise TaskConfigError("candidate instance_id must be non-empty")
        if instance_id in seen_ids:
            raise TaskConfigError(f"duplicate candidate instance_id: {instance_id}")
        seen_ids.add(instance_id)
        _require_sha40("candidate base commit", candidate.get("base_commit"))
    policy = config.get("exclusion_policy", {})
    if policy.get("infrastructure_retry_limit") != 1:
        raise TaskConfigError("R2 permits exactly one infrastructure retry")
    if policy.get("retry_requires_new_run_id") is not True:
        raise TaskConfigError("R2 retries must require a new run ID")


def validate_manifest(
    manifest: Mapping[str, Any], candidates: Mapping[str, Any]
) -> None:
    if manifest.get("schema_version") != "task-manifest-v0.2":
        raise TaskConfigError("unsupported task manifest schema")
    if manifest.get("freeze_status") not in {
        "pending_r2_docker_revalidation",
        "frozen",
    }:
        raise TaskConfigError("invalid task freeze status")
    for section in ("dataset", "harness"):
        if manifest.get(section) != candidates.get(section):
            raise TaskConfigError(f"manifest {section} differs from candidates config")
    selection = manifest.get("selection", {})
    index = selection.get("selected_candidate_index")
    ordered = candidates["candidates"]
    if not isinstance(index, int) or not 0 <= index < len(ordered):
        raise TaskConfigError("selected candidate index is outside frozen order")
    candidate = ordered[index]
    task = manifest.get("task", {})
    for task_key, candidate_key in (
        ("instance_id", "instance_id"),
        ("base_commit", "base_commit"),
    ):
        if task.get(task_key) != candidate.get(candidate_key):
            raise TaskConfigError(f"manifest task {task_key} differs from candidate")
    _require_sha40("environment setup commit", task.get("environment_setup_commit"))
    _require_sha40("prepared image commit", task.get("prepared_image_commit"))
    _require_sha256("problem statement", task.get("problem_statement_sha256"))
    for name in ("reference_patch", "test_patch", "baseline_prediction"):
        record = task.get(name, {})
        relative = record.get("path")
        _require_sha256(f"{name} digest", record.get("sha256"))
        if not isinstance(relative, str) or not (ROOT / relative).is_file():
            raise TaskConfigError(f"missing {name} file: {relative}")
        if sha256_file(ROOT / relative) != record["sha256"]:
            raise TaskConfigError(f"{name} digest differs from tracked file")
    baseline = task["baseline_prediction"]
    if "inert" not in baseline.get("identity", ""):
        raise TaskConfigError("baseline prediction must be explicitly marked inert")
    image = task.get("docker_image", {})
    reference = image.get("reference", "")
    if image.get("platform") != "linux/amd64" or not re.search(
        r"@sha256:[0-9a-f]{64}$", reference
    ):
        raise TaskConfigError("task image must be an immutable linux/amd64 reference")
    execution = manifest.get("execution", {})
    if execution.get("gpu_metrics") != "not_applicable":
        raise TaskConfigError("R2 GPU metrics must be not_applicable")
    if execution.get("max_workers") != 1:
        raise TaskConfigError("single-task R2 must use one harness worker")
    oracle = task.get("oracle", {})
    if not oracle.get("fail_to_pass") or not oracle.get("pass_to_pass"):
        raise TaskConfigError("task oracle must freeze FAIL_TO_PASS and PASS_TO_PASS")
    pilot = manifest.get("evidence", {}).get("pilot", {})
    if pilot.get("evidence_class") != "development_evidence_only":
        raise TaskConfigError("pilot must be marked as development evidence only")
    if pilot.get("formal_r2_eligible") is not False:
        raise TaskConfigError("pilot results must be ineligible for formal R2")
    if pilot.get("required_attempts_per_mode") != 1:
        raise TaskConfigError("local pilot requires exactly one attempt per mode")


def load_and_validate(
    candidate_path: Path = DEFAULT_CANDIDATES,
    manifest_path: Path = DEFAULT_MANIFEST,
) -> tuple[dict[str, Any], dict[str, Any]]:
    candidates = load_document(candidate_path)
    manifest = load_document(manifest_path)
    validate_candidates(candidates)
    validate_manifest(manifest, candidates)
    return candidates, manifest


def installed_harness_commit() -> str:
    """Read the PEP 610 commit recorded by a VCS installation of swebench."""
    try:
        distribution = importlib.metadata.distribution("swebench")
    except importlib.metadata.PackageNotFoundError as exc:
        raise InfrastructureError(
            "swebench is not installed; run: python3 -m pip install -r requirements-r2.txt"
        ) from exc
    direct_url_text = distribution.read_text("direct_url.json")
    if not direct_url_text:
        raise InfrastructureError(
            "swebench lacks direct_url.json; install the pinned Git requirement"
        )
    try:
        direct_url = json.loads(direct_url_text)
        commit = direct_url["vcs_info"]["commit_id"]
    except (KeyError, json.JSONDecodeError, TypeError) as exc:
        raise InfrastructureError("cannot read installed swebench VCS commit") from exc
    if not SHA40.fullmatch(commit):
        raise InfrastructureError("installed swebench commit is not immutable")
    return commit


def _run_checked(command: Sequence[str], *, cwd: Path | None = None) -> str:
    completed = subprocess.run(
        list(command),
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise InfrastructureError(f"command failed ({completed.returncode}): {detail}")
    return completed.stdout.strip()


def docker_server_architecture() -> str:
    if shutil.which("docker") is None:
        raise InfrastructureError("docker executable not found")
    return _run_checked(["docker", "info", "--format", "{{.Architecture}}"])


def preflight_environment(manifest: Mapping[str, Any], output_dir: Path) -> dict[str, Any]:
    execution = manifest["execution"]
    output_dir.mkdir(parents=True, exist_ok=True)
    machine = platform.machine().lower()
    docker_arch = docker_server_architecture().lower()
    accepted = {"x86_64", "amd64"}
    if machine not in accepted or docker_arch not in accepted:
        raise InfrastructureError(
            f"R2 requires an x86_64 Docker host; host={machine}, docker={docker_arch}"
        )
    docker_root_text = _run_checked(
        ["docker", "info", "--format", "{{.DockerRootDir}}"]
    )
    docker_root = Path(docker_root_text)
    if not docker_root.is_dir():
        raise InfrastructureError(
            f"Docker root directory is not visible on the host: {docker_root}"
        )
    free_gib = shutil.disk_usage(docker_root).free / 1024**3
    if free_gib < execution["minimum_free_disk_gib"]:
        raise InfrastructureError(
            f"R2 requires {execution['minimum_free_disk_gib']} GiB free; found {free_gib:.2f} GiB"
        )
    actual_harness = installed_harness_commit()
    expected_harness = manifest["harness"]["commit"]
    if actual_harness != expected_harness:
        raise InfrastructureError(
            f"swebench commit mismatch: expected {expected_harness}, found {actual_harness}"
        )
    return {
        "host_platform": platform.platform(),
        "host_architecture": machine,
        "docker_server_architecture": docker_arch,
        "docker_root_dir": str(docker_root),
        "python": platform.python_version(),
        "swebench_commit": actual_harness,
        "disk_free_gib": round(free_gib, 2),
        "gpu": "unused",
        "gpu_metrics": "not_applicable",
    }


def materialize_candidate_dataset(
    candidates: Mapping[str, Any],
    manifest: Mapping[str, Any],
    candidate_index: int,
    destination: Path,
) -> tuple[dict[str, Any], str]:
    """Download one exact dataset revision and write one row for the harness."""
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise InfrastructureError("the pinned swebench environment lacks datasets") from exc
    ordered = candidates["candidates"]
    if not 0 <= candidate_index < len(ordered):
        raise TaskConfigError("candidate index is outside frozen order")
    candidate = ordered[candidate_index]
    dataset_config = candidates["dataset"]
    dataset = load_dataset(
        dataset_config["name"],
        revision=dataset_config["revision"],
        split=dataset_config["split"],
    )
    row = dict(dataset[candidate["dataset_row_index"]])
    for key in ("instance_id", "repo", "base_commit"):
        if row.get(key) != candidate[key]:
            raise InfrastructureError(
                f"frozen dataset row {key} mismatch: {row.get(key)!r} != {candidate[key]!r}"
            )
    task = manifest["task"]
    expected_fields = {
        "patch": task["reference_patch"]["sha256"],
        "test_patch": task["test_patch"]["sha256"],
        "problem_statement": task["problem_statement_sha256"],
    }
    for field, expected in expected_fields.items():
        actual = sha256_bytes(row[field].encode("utf-8"))
        if actual != expected:
            raise InfrastructureError(
                f"frozen dataset {field} digest mismatch: {actual} != {expected}"
            )
    if row.get("environment_setup_commit") != task["environment_setup_commit"]:
        raise InfrastructureError("environment setup commit differs from manifest")
    payload = json.dumps([row], sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"
    destination.write_bytes(payload)
    return row, sha256_bytes(payload)


def prepare_pinned_image(manifest: Mapping[str, Any]) -> dict[str, str]:
    image = manifest["task"]["docker_image"]
    source = image["reference"]
    digest = source.rsplit("@sha256:", 1)[1]
    _run_checked(["docker", "pull", "--platform", image["platform"], source])
    inspection = json.loads(_run_checked(["docker", "image", "inspect", source]))[0]
    repo_digests = inspection.get("RepoDigests") or []
    if not any(value.endswith("@sha256:" + digest) for value in repo_digests):
        raise InfrastructureError("pulled image does not expose the frozen digest")
    repository = source.split("@", 1)[0]
    if repository.startswith("docker.io/"):
        repository = repository[len("docker.io/") :]
    tag = "r2-" + digest[:12]
    tagged = f"{repository}:{tag}"
    _run_checked(["docker", "tag", source, tagged])
    namespace, image_name = repository.split("/", 1)
    return {
        "source": source,
        "source_digest": "sha256:" + digest,
        "local_tag": tagged,
        "namespace": namespace,
        "image_name": image_name,
        "instance_image_tag": tag,
        "image_id": inspection["Id"],
    }


def inspect_workspace_tree(manifest: Mapping[str, Any], image_ref: str) -> str:
    task = manifest["task"]
    revision = task["prepared_image_commit"] + "^{tree}"
    value = _run_checked(
        [
            "docker",
            "run",
            "--rm",
            "--platform",
            task["docker_image"]["platform"],
            "--network",
            "none",
            image_ref,
            "git",
            "-C",
            "/testbed",
            "rev-parse",
            revision,
        ]
    )
    if not SHA40.fullmatch(value):
        raise InfrastructureError(f"invalid workspace tree digest: {value!r}")
    return value


def write_prediction(
    manifest: Mapping[str, Any], mode: str, destination: Path
) -> str:
    if mode == "reference":
        return "gold"
    if mode != "baseline":
        raise TaskConfigError(f"unsupported R2 mode: {mode}")
    task = manifest["task"]
    patch = (ROOT / task["baseline_prediction"]["path"]).read_text(encoding="utf-8")
    prediction = [
        {
            "instance_id": task["instance_id"],
            "model_name_or_path": "r2-inert-baseline",
            "model_patch": patch,
        }
    ]
    destination.write_text(
        json.dumps(prediction, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return str(destination)


def build_harness_command(
    manifest: Mapping[str, Any],
    *,
    dataset_path: Path,
    predictions_path: str,
    run_id: str,
    report_dir: Path,
    image: Mapping[str, str],
) -> list[str]:
    execution = manifest["execution"]
    return [
        sys.executable,
        "-m",
        "swebench.harness.run_evaluation",
        "--dataset_name",
        str(dataset_path),
        "--split",
        manifest["dataset"]["split"],
        "--predictions_path",
        predictions_path,
        "--instance_ids",
        manifest["task"]["instance_id"],
        "--max_workers",
        str(execution["max_workers"]),
        "--run_id",
        run_id,
        "--cache_level",
        execution["cache_level"],
        "--clean",
        str(execution["clean_images"]),
        "--timeout",
        str(execution["timeout_seconds"]),
        "--namespace",
        image["namespace"],
        "--instance_image_tag",
        image["instance_image_tag"],
        "--report_dir",
        str(report_dir),
    ]


def stream_process(command: Sequence[str], cwd: Path, stdout_path: Path, stderr_path: Path) -> int:
    """Mirror harness output live while preserving separate stdout/stderr logs."""
    process = subprocess.Popen(
        list(command),
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
    )

    def pump(source: Any, destination: Path, label: str) -> None:
        with destination.open("w", encoding="utf-8") as handle:
            for line in iter(source.readline, ""):
                handle.write(line)
                handle.flush()
                print(f"[{label}] {line}", end="", flush=True)
        source.close()

    threads = [
        threading.Thread(target=pump, args=(process.stdout, stdout_path, "stdout")),
        threading.Thread(target=pump, args=(process.stderr, stderr_path, "stderr")),
    ]
    for thread in threads:
        thread.start()
    return_code = process.wait()
    for thread in threads:
        thread.join()
    return return_code


def find_instance_report(attempt_dir: Path, instance_id: str) -> tuple[Path, dict[str, Any]]:
    matches = [
        path
        for path in attempt_dir.rglob("report.json")
        if instance_id in path.parts
    ]
    if len(matches) != 1:
        raise InfrastructureError(
            f"expected one report.json for {instance_id}, found {len(matches)}"
        )
    document = json.loads(matches[0].read_text(encoding="utf-8"))
    report = document.get(instance_id, document)
    if not isinstance(report, dict) or not isinstance(report.get("resolved"), bool):
        raise InfrastructureError("official report lacks a boolean resolved verdict")
    return matches[0], report


def oracle_matches(
    mode: str, report: Mapping[str, Any], manifest: Mapping[str, Any]
) -> tuple[bool, list[str]]:
    oracle = manifest["task"]["oracle"]
    tests = report.get("tests_status", {})
    fail_to_pass = tests.get("FAIL_TO_PASS", {})
    pass_to_pass = tests.get("PASS_TO_PASS", {})
    ftp_success = set(fail_to_pass.get("success", []))
    ftp_failure = set(fail_to_pass.get("failure", []))
    ptp_success = set(pass_to_pass.get("success", []))
    expected_ftp = set(oracle["fail_to_pass"])
    expected_ptp = set(oracle["pass_to_pass"])
    problems: list[str] = []
    if ptp_success != expected_ptp:
        problems.append("PASS_TO_PASS success set differs from manifest")
    if mode == "baseline":
        if report["resolved"]:
            problems.append("inert baseline unexpectedly resolved the task")
        if ftp_failure != expected_ftp or ftp_success:
            problems.append("baseline FAIL_TO_PASS verdict differs from manifest")
    elif mode == "reference":
        if not report["resolved"]:
            problems.append("official reference patch did not resolve the task")
        if ftp_success != expected_ftp or ftp_failure:
            problems.append("reference FAIL_TO_PASS verdict differs from manifest")
    else:
        problems.append(f"unsupported mode: {mode}")
    return not problems, problems


def build_pilot_docker_command(
    manifest: Mapping[str, Any], mode: str
) -> list[str]:
    """Build the local emulation command used only for development evidence."""
    if mode not in {"baseline", "reference"}:
        raise TaskConfigError(f"unsupported pilot mode: {mode}")
    task = manifest["task"]
    task_dir = ROOT / Path(task["test_patch"]["path"]).parent
    prepared_commit = task["prepared_image_commit"]
    script_parts = [
        "set -eu",
        "cd /testbed",
        f"git reset --hard {prepared_commit} >/dev/null",
        "git apply /frozen/test.patch",
    ]
    if mode == "baseline":
        script_parts.append("git apply /frozen/baseline.patch")
    else:
        script_parts.append("git apply /frozen/reference.patch")
    script_parts.append(
        "/opt/miniconda3/envs/testbed/bin/pytest -rA "
        "astropy/modeling/tests/test_separable.py"
    )
    return [
        "docker",
        "run",
        "--rm",
        "--platform",
        task["docker_image"]["platform"],
        "--network",
        "none",
        "-v",
        f"{task_dir}:/frozen:ro",
        task["docker_image"]["reference"],
        "/bin/bash",
        "-lc",
        "; ".join(script_parts),
    ]


def pilot_output_matches(mode: str, exit_code: int, output: str) -> bool:
    """Check the frozen 15-test development oracle without claiming R2 evidence."""
    if mode == "baseline":
        return exit_code == 1 and "2 failed, 13 passed" in output
    if mode == "reference":
        return exit_code == 0 and "15 passed" in output
    raise TaskConfigError(f"unsupported pilot mode: {mode}")


def run_pilot_attempt(
    manifest: Mapping[str, Any], *, mode: str, run_id: str, output_dir: Path
) -> dict[str, Any]:
    """Run one amd64-emulated smoke attempt and save a small, non-formal result."""
    if not RUN_ID.fullmatch(run_id):
        raise TaskConfigError("run ID must be 3-128 safe filename characters")
    result_path = output_dir / f"{mode}-{run_id}.json"
    if result_path.exists():
        raise TaskConfigError(f"pilot result already exists: {result_path}")
    if shutil.which("docker") is None:
        raise InfrastructureError("docker executable not found")
    command = build_pilot_docker_command(manifest, mode)
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    output = completed.stdout
    summary_lines = [
        line.strip()
        for line in output.splitlines()
        if re.search(r"(?:failed|passed).+in [0-9.]+s", line)
    ]
    matched = pilot_output_matches(mode, completed.returncode, output)
    if not summary_lines:
        status = "INFRASTRUCTURE_FAILURE"
    else:
        status = "PASS" if matched else "FAIL"
    result = {
        "schema_version": "r2-pilot-attempt-v1",
        "evidence_class": "development_evidence_only",
        "formal_r2_eligible": False,
        "status": status,
        "mode": mode,
        "run_id": run_id,
        "host_platform": platform.platform(),
        "host_architecture": platform.machine().lower(),
        "container_platform": manifest["task"]["docker_image"]["platform"],
        "image_reference": manifest["task"]["docker_image"]["reference"],
        "exit_code": completed.returncode,
        "duration_seconds": round(time.monotonic() - started, 3),
        "summary": summary_lines[-1] if summary_lines else "test summary not found",
        "output_tail": output.splitlines()[-40:],
    }
    atomic_json(result_path, result)
    return result


def _run_id_seen(output_dir: Path, run_id: str) -> bool:
    for result_path in output_dir.rglob("attempt_result.json"):
        try:
            if json.loads(result_path.read_text(encoding="utf-8")).get("run_id") == run_id:
                return True
        except (OSError, json.JSONDecodeError):
            continue
    return False


def summarize_attempts(output_dir: Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    for path in sorted(output_dir.rglob("attempt_result.json")):
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if item.get("instance_id") == manifest["task"]["instance_id"]:
            attempts.append(item)
    required = manifest["evidence"]["required_attempts_per_mode"]
    blockers: list[str] = []
    selected: dict[str, list[dict[str, Any]]] = {}
    for mode in manifest["evidence"]["required_modes"]:
        passed = [item for item in attempts if item.get("mode") == mode and item.get("status") == "PASS"]
        selected[mode] = passed
        if len(passed) < required:
            blockers.append(f"{mode}_requires_{required}_passing_attempts")
    passing = [item for values in selected.values() for item in values[:required]]
    if passing:
        for field in ("workspace_tree_sha", "image_digest", "dataset_row_sha256"):
            if len({item.get(field) for item in passing}) != 1:
                blockers.append(f"{field}_mismatch")
    run_ids = [item.get("run_id") for item in passing]
    if len(run_ids) != len(set(run_ids)):
        blockers.append("run_id_reuse")
    status = "PASS" if not blockers else "REVISE"
    return {
        "schema_version": "r2-selection-report-v1",
        "status": status,
        "instance_id": manifest["task"]["instance_id"],
        "candidate_index": manifest["selection"]["selected_candidate_index"],
        "required_attempts_per_mode": required,
        "attempts": [
            {
                "mode": item.get("mode"),
                "run_id": item.get("run_id"),
                "status": item.get("status"),
                "result_path": item.get("result_path"),
            }
            for item in attempts
        ],
        "identity": {
            "dataset_revision": manifest["dataset"]["revision"],
            "harness_commit": manifest["harness"]["commit"],
            "base_commit": manifest["task"]["base_commit"],
            "image_digest": passing[0].get("image_digest") if passing else None,
            "workspace_tree_sha": passing[0].get("workspace_tree_sha") if passing else None,
        },
        "blockers": blockers,
    }


def run_candidate(
    candidates: Mapping[str, Any],
    manifest: Mapping[str, Any],
    *,
    candidate_index: int,
    mode: str,
    run_id: str,
    output_dir: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if not RUN_ID.fullmatch(run_id):
        raise TaskConfigError("run ID must be 3-128 safe filename characters")
    if _run_id_seen(output_dir, run_id):
        raise TaskConfigError(f"run ID has already been used: {run_id}")
    if candidate_index != manifest["selection"]["selected_candidate_index"]:
        raise TaskConfigError("this manifest only supports its frozen candidate index")
    instance_id = manifest["task"]["instance_id"]
    attempt_dir = output_dir / instance_id / mode / run_id
    if attempt_dir.exists():
        raise TaskConfigError(f"attempt directory already exists: {attempt_dir}")
    attempt_dir.mkdir(parents=True)
    result_path = attempt_dir / "attempt_result.json"
    started = time.monotonic()
    result: dict[str, Any] = {
        "schema_version": "r2-attempt-result-v1",
        "status": "INFRASTRUCTURE_FAILURE",
        "instance_id": instance_id,
        "candidate_index": candidate_index,
        "mode": mode,
        "run_id": run_id,
        "result_path": str(result_path),
        "gpu": "unused",
        "gpu_metrics": "not_applicable",
    }
    try:
        environment = preflight_environment(manifest, output_dir)
        atomic_json(attempt_dir / "environment.json", environment)
        preparation_started = time.monotonic()
        dataset_path = attempt_dir / "dataset-row.json"
        _, dataset_digest = materialize_candidate_dataset(
            candidates, manifest, candidate_index, dataset_path
        )
        predictions_path = write_prediction(
            manifest, mode, attempt_dir / "predictions.json"
        )
        image = prepare_pinned_image(manifest)
        tree_sha = inspect_workspace_tree(manifest, image["local_tag"])
        result.update(
            {
                "dataset_row_sha256": dataset_digest,
                "image_digest": image["source_digest"],
                "image_id": image["image_id"],
                "workspace_tree_sha": tree_sha,
                "preparation_seconds": round(time.monotonic() - preparation_started, 3),
            }
        )
        report_dir = attempt_dir / "reports"
        command = build_harness_command(
            manifest,
            dataset_path=dataset_path,
            predictions_path=predictions_path,
            run_id=run_id,
            report_dir=report_dir,
            image=image,
        )
        atomic_json(attempt_dir / "command.json", {"argv": command, "shell": False})
        harness_started = time.monotonic()
        exit_code = stream_process(
            command,
            attempt_dir,
            attempt_dir / "stdout.log",
            attempt_dir / "stderr.log",
        )
        harness_seconds = round(time.monotonic() - harness_started, 3)
        result.update({"exit_code": exit_code, "test_wall_seconds": harness_seconds})
        if exit_code != 0:
            raise InfrastructureError(f"official harness exited with code {exit_code}")
        report_path, report = find_instance_report(attempt_dir, instance_id)
        matched, problems = oracle_matches(mode, report, manifest)
        result.update(
            {
                "official_report_path": str(report_path),
                "resolved": report["resolved"],
                "oracle_problems": problems,
                "status": "PASS" if matched else "FAIL",
            }
        )
    except Exception as exc:
        result["error_type"] = type(exc).__name__
        result["error"] = str(exc)
    result["wall_seconds"] = round(time.monotonic() - started, 3)
    atomic_json(result_path, result)
    summary = summarize_attempts(output_dir, manifest)
    atomic_json(output_dir / "selection_report.json", summary)
    return result, summary

"""Shared adapter for the validated SWE-bench oracle artifacts.

The historical oracle directory contains frozen inputs, official harness logs,
reports, and summaries rather than a reusable Python package.  This module is
the small schema adapter around that artifact contract.  It deliberately does
not implement grading: the official ``swebench eval`` command remains the only
evaluator and ``resolved`` is read from its per-instance ``report.json``.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.metadata
import json
import platform
import re
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable


GRANULARITIES = {"G1": 1, "G2": 2, "G4": 4}


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _json_or(path: Path, default: Any) -> Any:
    try:
        return _json(path)
    except (OSError, ValueError):
        return default


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _first(*values: Any) -> Any:
    for value in values:
        if value is not None and value != "":
            return value
    return None


def _as_patch(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("model_patch/final_patch must be a string or null")
    return value


def _prediction_patch(path: Path, instance_id: str) -> str | None:
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("instance_id") == instance_id:
            return _as_patch(row.get("model_patch"))
    return None


def _attack_fields(result: dict[str, Any], metadata: dict[str, Any]) -> tuple[str, str | None]:
    attack = result.get("attack_metadata")
    if not isinstance(attack, dict):
        attack = metadata.get("attack_metadata")
    if not isinstance(attack, dict):
        attack = metadata.get("attack")
    if not isinstance(attack, dict):
        attack = {}
    condition = str(_first(result.get("condition"), metadata.get("condition"), "clean"))
    family = _first(attack.get("attack_family"), result.get("attack_family"), metadata.get("attack_family"))
    attack_id = _first(attack.get("attack_id"), result.get("attack_id"), metadata.get("attack_id"))
    if condition == "clean":
        return "clean", None
    return str(family or "unspecified"), str(attack_id) if attack_id is not None else None


@dataclass(frozen=True)
class NormalizedRun:
    run_id: str
    instance_id: str
    treatment: str
    granularity_condition: str | None
    max_ops_per_action: int | None
    condition: str
    attack_family: str
    attack_id: str | None
    rollout: int | None
    patch: str
    run_dir: Path
    result: dict[str, Any]
    metadata: dict[str, Any]
    formal: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "instance_id": self.instance_id,
            "treatment": self.treatment,
            "granularity_condition": self.granularity_condition,
            "max_ops_per_action": self.max_ops_per_action,
            "condition": self.condition,
            "attack_family": self.attack_family,
            "attack_id": self.attack_id,
            "rollout": self.rollout,
            "formal": self.formal,
            "run_directory": str(self.run_dir),
        }


def _patch_from_run(run_dir: Path, result: dict[str, Any], instance_id: str) -> str:
    candidates: list[tuple[str, str]] = []
    patch_path = run_dir / "patch.diff"
    if patch_path.is_file():
        candidates.append(("patch.diff", _text(patch_path)))
    if "final_patch" in result and result.get("final_patch") is not None:
        candidates.append(("result.json:final_patch", _as_patch(result["final_patch"]) or ""))
    prediction = _prediction_patch(run_dir / "prediction.jsonl", instance_id)
    if prediction is not None:
        candidates.append(("prediction.jsonl:model_patch", prediction))
    if not candidates:
        raise ValueError(f"run {run_dir.name} has no final patch source")
    patch = candidates[0][1]
    inconsistent = [(source, value) for source, value in candidates if value != patch]
    if inconsistent:
        names = ", ".join(source for source, _ in candidates)
        raise ValueError(f"run {run_dir.name} has inconsistent patch sources: {names}")
    return patch


def load_run(run_dir: Path, plan_spec: dict[str, Any] | None = None) -> NormalizedRun:
    result_path = run_dir / "result.json"
    if not result_path.is_file():
        raise ValueError(f"run has no result.json: {run_dir}")
    result = _json(result_path)
    metadata = _json_or(run_dir / "metadata.json", {})
    if not isinstance(result, dict) or not isinstance(metadata, dict):
        raise ValueError(f"run metadata is not an object: {run_dir}")
    plan_spec = plan_spec or {}
    run_id = str(_first(metadata.get("run_id"), result.get("run_id"), plan_spec.get("run_id"), run_dir.name))
    if run_id != run_dir.name:
        raise ValueError(f"run_id mismatch for {run_dir}: {run_id}")
    marker_path = run_dir / "COMPLETE.json"
    if marker_path.is_file():
        marker = _json(marker_path)
        if marker.get("status") != "completed" or marker.get("run_id") != run_id:
            raise ValueError(f"run is not complete: {run_dir}")
    instance_id = str(_first(
        result.get("task_id"), result.get("instance_id"), metadata.get("task_id"),
        metadata.get("instance_id"), plan_spec.get("task_id"), plan_spec.get("instance_id"),
    ) or "")
    if not instance_id:
        raise ValueError(f"run has no task/instance id: {run_dir}")
    granularity = _first(
        result.get("granularity_condition"), result.get("G"), metadata.get("granularity_condition"),
        metadata.get("G"), plan_spec.get("granularity_condition"), plan_spec.get("G"),
    )
    formal = granularity is not None
    if formal:
        granularity = str(granularity)
        if granularity not in GRANULARITIES:
            raise ValueError(f"unsupported formal granularity {granularity!r} in {run_id}")
        treatment = granularity
        max_ops_value = _first(
            result.get("max_ops_per_action"), metadata.get("max_ops_per_action"),
            plan_spec.get("max_ops_per_action"), GRANULARITIES[granularity],
        )
        max_ops = int(max_ops_value)
        if max_ops != GRANULARITIES[granularity]:
            raise ValueError(f"{run_id} has inconsistent max_ops_per_action={max_ops}")
    else:
        treatment = str(_first(result.get("interface"), metadata.get("interface"), "legacy"))
        granularity = None
        max_ops = None
    condition = str(_first(result.get("condition"), metadata.get("condition"), plan_spec.get("condition"), "clean"))
    attack_family, attack_id = _attack_fields(result, metadata)
    rollout_value = _first(
        result.get("rollout"), metadata.get("rollout"), plan_spec.get("rollout"),
        result.get("seed"), metadata.get("seed"), plan_spec.get("seed"),
    )
    rollout = int(rollout_value) if rollout_value is not None else None
    return NormalizedRun(
        run_id, instance_id, treatment, granularity, max_ops, condition,
        attack_family, attack_id, rollout, _patch_from_run(run_dir, result, instance_id),
        run_dir, result, metadata, formal,
    )


def _run_root(experiment_root: Path) -> Path:
    if (experiment_root / "result.json").is_file():
        return experiment_root.parent
    if (experiment_root / "runs").is_dir():
        return experiment_root / "runs"
    if (experiment_root / "input" / "runs").is_dir():
        return experiment_root / "input" / "runs"
    raise ValueError(f"cannot find formal runs/ or legacy input/runs/ under {experiment_root}")


def load_runs(experiment_root: Path, run_id: str | None = None) -> list[NormalizedRun]:
    experiment_root = experiment_root.resolve()
    run_root = _run_root(experiment_root)
    plan_by_id: dict[str, dict[str, Any]] = {}
    plan_path = experiment_root / "PLAN.json"
    if plan_path.is_file():
        plan = _json(plan_path)
        plan_by_id = {str(item["run_id"]): item for item in plan.get("runs", [])}
    if run_id:
        directories = [run_root / run_id]
    else:
        planned_ids = list(plan_by_id)
        directories = [run_root / item for item in planned_ids] if planned_ids else sorted(
            path for path in run_root.iterdir() if path.is_dir()
        )
    if not directories:
        raise ValueError(f"no run directories found under {run_root}")
    runs: list[NormalizedRun] = []
    for directory in directories:
        if not directory.is_dir():
            raise ValueError(f"missing run directory: {directory}")
        runs.append(load_run(directory, plan_by_id.get(directory.name)))
    return runs


def _model_name(run: NormalizedRun) -> str:
    model = run.metadata.get("model")
    if isinstance(model, dict) and model.get("name"):
        return str(model["name"])
    return str(run.result.get("model_name_or_path", "interface-experiment"))


def prediction_record(run: NormalizedRun) -> dict[str, str]:
    return {
        "instance_id": run.instance_id,
        "model_name_or_path": _model_name(run),
        "model_patch": run.patch,
    }


def _manifest_row(run: NormalizedRun) -> dict[str, Any]:
    return {
        **run.as_dict(),
        "G": run.granularity_condition,
        "empty_patch": not bool(run.patch),
        "evaluation_status": "not_attempted_empty_patch" if not run.patch else "pending_official_oracle",
        "evaluator_status": "not_attempted_empty_patch" if not run.patch else "pending_official_oracle",
    }


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def prepare_predictions(
    experiment_root: Path,
    run_id: str | None = None,
    output: Path | None = None,
) -> tuple[Path, list[dict[str, Any]]]:
    """Export one prediction file per rollout, never one file per instance.

    The official harness accepts one prediction per instance in an invocation.
    Keeping one file per ``run_id`` is what prevents repeated rollouts from
    overwriting each other while retaining the official input format.
    """

    runs = load_runs(experiment_root, run_id)
    manifests = [_manifest_row(run) for run in runs]
    if len(runs) == 1:
        destination = output if output and output.suffix == ".jsonl" else (output or experiment_root / "oracle" / "predictions")
        if destination.suffix != ".jsonl":
            destination = destination / f"{runs[0].run_id}.jsonl"
        _write_jsonl(destination, [prediction_record(runs[0])] if runs[0].patch else [])
        manifest_path = destination.with_name(destination.stem + ".manifest.json")
    else:
        destination = output or experiment_root / "oracle" / "predictions"
        if destination.suffix == ".jsonl":
            raise ValueError("multiple rollouts require an output directory, not one .jsonl file")
        destination.mkdir(parents=True, exist_ok=True)
        for run in runs:
            _write_jsonl(destination / f"{run.run_id}.jsonl", [prediction_record(run)] if run.patch else [])
        manifest_path = destination / "manifest.json"
    manifest_path.write_text(json.dumps(manifests, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return destination, manifests


def build_official_command(
    swebench_executable: str,
    task_metadata: Path,
    prediction: Path,
    official_run_id: str,
    instance_id: str,
    timeout: int,
) -> list[str]:
    """Build the validated v6.1 ``swebench eval`` invocation."""

    return [
        swebench_executable, "eval", str(task_metadata), "-p", str(prediction),
        "-r", official_run_id, "-i", instance_id, "-j", "1", "-t", str(timeout),
    ]


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def _candidate_report_paths(root: Path, official_run_id: str, filename: str) -> list[Path]:
    return sorted(
        path for path in root.rglob(filename)
        if official_run_id in str(path)
    )


def _report_entry(report: Any, instance_id: str) -> dict[str, Any] | None:
    if isinstance(report, dict):
        if isinstance(report.get(instance_id), dict):
            return report[instance_id]
        for key in ("results", "instances"):
            if isinstance(report.get(key), list):
                for row in report[key]:
                    if isinstance(row, dict) and row.get("instance_id") == instance_id:
                        return row
        if report.get("instance_id") == instance_id:
            return report
    if isinstance(report, list):
        for row in report:
            if isinstance(row, dict) and row.get("instance_id") == instance_id:
                return row
    return None


def parse_official_outputs(
    report_path: Path | None,
    results_path: Path | None,
    instance_id: str,
) -> dict[str, Any]:
    """Parse official output without inferring success from patch presence."""

    report = _json_or(report_path, None) if report_path else None
    entry = _report_entry(report, instance_id)
    if entry is not None and "resolved" in entry:
        infra = bool(entry.get("infra_failure", False))
        return {
            "evaluation_attempted": True,
            "evaluation_status": "infra_failure" if infra else "completed",
            "patch_applied": entry.get("patch_successfully_applied"),
            "resolved": None if infra else bool(entry["resolved"]),
            "infrastructure_failure": infra,
            "infrastructure_failure_reason": entry.get("error") if infra else None,
            "failure_category": (
                "infrastructure_failure" if infra
                else "patch_apply_failure" if entry.get("patch_successfully_applied") is False
                else "test_failure" if not entry["resolved"]
                else None
            ),
            "official_report_path": str(report_path) if report_path else None,
            "official_result_path": str(results_path) if results_path else None,
        }
    summary = _json_or(results_path, {}) if results_path else {}
    if not isinstance(summary, dict):
        summary = {}
    if instance_id in set(summary.get("infra_failure_ids", [])):
        reason = summary.get("failure_reasons", {}).get(instance_id)
        return {
            "evaluation_attempted": True, "evaluation_status": "infra_failure",
            "patch_applied": None, "resolved": None, "infrastructure_failure": True,
            "infrastructure_failure_reason": reason or "official harness reported infra_failure",
            "failure_category": "infrastructure_failure",
            "official_report_path": str(report_path) if report_path else None,
            "official_result_path": str(results_path) if results_path else None,
        }
    error_ids = set(summary.get("error_ids", [])) | set(summary.get("incomplete_ids", []))
    if instance_id in error_ids or not entry:
        return {
            "evaluation_attempted": True, "evaluation_status": "infra_failure",
            "patch_applied": None, "resolved": None, "infrastructure_failure": True,
            "infrastructure_failure_reason": "official report.json was not produced for the instance",
            "failure_category": "infrastructure_failure",
            "official_report_path": str(report_path) if report_path else None,
            "official_result_path": str(results_path) if results_path else None,
        }
    return {
        "evaluation_attempted": True, "evaluation_status": "infra_failure",
        "patch_applied": None, "resolved": None, "infrastructure_failure": True,
        "infrastructure_failure_reason": "official output could not be parsed",
        "failure_category": "infrastructure_failure",
        "official_report_path": str(report_path) if report_path else None,
        "official_result_path": str(results_path) if results_path else None,
    }


def _base_oracle_row(run: NormalizedRun) -> dict[str, Any]:
    row = {
        "run_id": run.run_id,
        "instance_id": run.instance_id,
        "task": run.instance_id,
        "treatment": run.treatment,
        "interface": run.treatment if not run.formal else None,
        "granularity_condition": run.granularity_condition,
        "G": run.granularity_condition,
        "max_ops_per_action": run.max_ops_per_action,
        "condition": run.condition,
        "attack_family": run.attack_family,
        "attack_id": run.attack_id,
        "rollout": run.rollout,
        "seed": run.rollout if not run.formal else None,
        "patch_nonempty": bool(run.patch),
        "evaluation_attempted": False,
        "evaluation_status": "not_attempted_empty_patch" if not run.patch else "pending_official_oracle",
        "patch_applied": None,
        "resolved": None,
        "infrastructure_failure": False,
        "infrastructure_failure_reason": None,
        "harness_log_path": None,
        "official_log_path": None,
        "failure_category": "empty_patch" if not run.patch else None,
        "patch_sha256": hashlib.sha256(run.patch.encode("utf-8")).hexdigest(),
        "patch_size_bytes": len(run.patch.encode("utf-8")),
        "attempts": 0,
        "retry_count": 0,
    }
    return row


CommandRunner = Callable[[list[str], Path, Path], int]


def run_command(command: list[str], log_path: Path, cwd: Path) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as handle:
        handle.write("$ " + " ".join(command) + "\n")
        handle.flush()
        completed = subprocess.run(command, cwd=cwd, stdout=handle, stderr=subprocess.STDOUT, check=False)
    return completed.returncode


def evaluate_run(
    run: NormalizedRun,
    output_root: Path,
    task_metadata: Path,
    *,
    swebench_executable: str = "swebench",
    timeout: int = 1800,
    max_attempts: int = 2,
    command_runner: CommandRunner = run_command,
) -> dict[str, Any]:
    if max_attempts < 1:
        raise ValueError("max_attempts must be positive")
    row = _base_oracle_row(run)
    if not run.patch:
        return row
    prediction = output_root / "predictions" / f"{run.run_id}.jsonl"
    _write_jsonl(prediction, [prediction_record(run)])
    run_output = output_root / "runs" / run.run_id
    run_output.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, max_attempts + 1):
        official_run_id = f"{_safe_name(run.run_id)}-attempt{attempt}"
        command = build_official_command(
            swebench_executable, task_metadata, prediction, official_run_id,
            run.instance_id, timeout,
        )
        log_path = output_root / "logs" / f"{_safe_name(run.run_id)}.attempt{attempt}.log"
        returncode = command_runner(command, log_path, output_root)
        reports = _candidate_report_paths(output_root, official_run_id, "report.json")
        results = _candidate_report_paths(output_root, official_run_id, "results.json")
        parsed = parse_official_outputs(
            reports[-1] if reports else None,
            results[-1] if results else None,
            run.instance_id,
        )
        parsed.update({
            "attempts": attempt,
            "retry_count": attempt - 1,
            "harness_log_path": str(log_path),
            "official_log_path": str(log_path),
            "official_run_id": official_run_id,
            "official_returncode": returncode,
        })
        row.update(parsed)
        if not row["infrastructure_failure"] or attempt == max_attempts:
            return row
    return row


def _find_task_metadata(experiment_root: Path, output_root: Path, explicit: Path | None) -> Path | None:
    if explicit:
        if not explicit.is_file():
            raise FileNotFoundError(explicit)
        return explicit
    candidates = [
        experiment_root / "tasks" / "verified_tasks.json",
        experiment_root / "tasks" / "swebench_verified.json",
        experiment_root / "tasks" / "task_metadata.json",
        experiment_root / "oracle" / "metadata" / "verified_tasks.json",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def collect_provenance(
    experiment_root: Path,
    repo_root: Path | None = None,
    swebench_harness_commit: str | None = None,
) -> dict[str, Any]:
    metadata = _json_or(experiment_root / "experiment_metadata.json", {})
    git = _json_or(experiment_root / "git_provenance.json", {})
    try:
        oracle_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo_root or Path(__file__).resolve().parents[1],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        oracle_commit = None
    try:
        swebench_version = importlib.metadata.version("swebench")
    except importlib.metadata.PackageNotFoundError:
        swebench_version = None
    try:
        docker_version = subprocess.check_output(
            ["docker", "--version"], text=True, stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        docker_version = None
    return {
        "experiment_branch": git.get("branch"),
        "experiment_commit": git.get("commit"),
        "experiment_id": metadata.get("experiment_id"),
        "oracle_code_commit": oracle_commit,
        "swebench_package_version": swebench_version,
        "swebench_harness_commit": swebench_harness_commit,
        "docker_version": docker_version,
        "host_os": platform.platform(),
        "architecture": platform.machine(),
        "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
    }


def run_official(
    experiment_root: Path,
    output_root: Path,
    *,
    task_metadata: Path | None = None,
    run_id: str | None = None,
    swebench_executable: str = "swebench",
    timeout: int = 1800,
    max_attempts: int = 2,
    command_runner: CommandRunner = run_command,
    repo_root: Path | None = None,
    swebench_harness_commit: str | None = None,
) -> list[dict[str, Any]]:
    runs = load_runs(experiment_root, run_id)
    output_root.mkdir(parents=True, exist_ok=True)
    metadata_path = _find_task_metadata(experiment_root, output_root, task_metadata)
    if any(run.patch for run in runs) and metadata_path is None:
        raise FileNotFoundError(
            "official task metadata is required; pass --task-metadata pointing to the verified task JSON"
        )
    rows = [
        evaluate_run(
            run, output_root, metadata_path or Path("missing-task-metadata.json"),
            swebench_executable=swebench_executable, timeout=timeout,
            max_attempts=max_attempts, command_runner=command_runner,
        )
        for run in runs
    ]
    _write_jsonl(output_root / "oracle_results.jsonl", rows)
    (output_root / "PROVENANCE.json").write_text(
        json.dumps(
            collect_provenance(experiment_root, repo_root, swebench_harness_commit),
            indent=2, sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )
    return rows


def _events(run: NormalizedRun) -> list[dict[str, Any]]:
    path = run.run_dir / "trajectory.jsonl"
    events = []
    if not path.is_file():
        return events
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict):
            events.append(value)
    return events


def rollout_metrics(run: NormalizedRun) -> dict[str, Any]:
    events = _events(run)
    actions = [item for item in events if item.get("event") in {"interface_action", "action"}]
    visible = [item for item in actions if item.get("status") != "finish"]
    backend = [item for item in events if item.get("event") == "backend_operation"]
    sizes = [int(item.get("operations_executed", item.get("backend_operations_executed", 0))) for item in actions]
    visible_sizes = [
        size for item, size in zip(actions, sizes) if item.get("status") != "finish"
    ]
    result = run.result
    action_count = int(result.get("actions", len(actions)))
    backend_count = int(result.get("backend_operations", len(backend)))
    runtime = result.get("runtime_seconds")
    return {
        "model_actions": action_count,
        "backend_operations": backend_count,
        "ops_per_observation": round(backend_count / len(visible), 6) if visible else 0.0,
        "batch_rate": round(sum(size > 1 for size in visible_sizes) / len(visible_sizes), 6) if visible_sizes else 0.0,
        "invalid_actions": sum(item.get("status") == "invalid" for item in actions),
        "input_tokens": int(result.get("input_tokens", 0)),
        "output_tokens": int(result.get("output_tokens", 0)),
        "runtime": runtime,
        "action_size_distribution": json.dumps(dict(sorted(Counter(sizes).items())), sort_keys=True),
        "attack_exposed": result.get("attack_exposed"),
        "attack_target_attempted": result.get("attack_target_attempted"),
        "blocked_attempt": result.get("attack_related_blocked", result.get("blocked_attempt")),
        "attack_success": result.get("attack_success"),
        "permission_denied_count": sum(item.get("status") == "denied" for item in backend),
    }


def _read_oracle_rows(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if not isinstance(row, dict):
            continue
        run_id = row.get("run_id") or row.get("run_directory")
        if run_id:
            rows[str(run_id)] = row
    return rows


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 6) if denominator else None


def summarize_experiment(
    experiment_root: Path,
    oracle_root: Path,
    *,
    output_root: Path | None = None,
    repo_root: Path | None = None,
    swebench_harness_commit: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    output_root = output_root or oracle_root
    runs = load_runs(experiment_root)
    oracle_rows = _read_oracle_rows(oracle_root / "oracle_results.jsonl")
    combined: list[dict[str, Any]] = []
    for run in runs:
        row = _base_oracle_row(run)
        row.update(rollout_metrics(run))
        row.update(oracle_rows.get(run.run_id, {}))
        row["patch_nonempty"] = bool(run.patch)
        row["resolved"] = oracle_rows.get(run.run_id, {}).get("resolved")
        combined.append(row)
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in combined:
        key = (
            str(row.get("granularity_condition") or row.get("treatment")),
            str(row.get("condition")),
            str(row.get("attack_family") or "clean"),
        )
        groups.setdefault(key, []).append(row)
    summaries: list[dict[str, Any]] = []
    for (treatment, condition, attack_family), group in sorted(groups.items()):
        infra = sum(bool(row.get("infrastructure_failure")) for row in group)
        valid_agent_runs = len(group) - infra
        nonempty_evaluated = sum(bool(row.get("patch_nonempty")) and row.get("evaluation_attempted") for row in group)
        resolved = sum(row.get("resolved") is True for row in group)
        summaries.append({
            "granularity_condition": treatment if treatment in GRANULARITIES else None,
            "treatment": treatment,
            "condition": condition,
            "attack_family": attack_family,
            "total_agent_runs": len(group),
            "valid_agent_runs": valid_agent_runs,
            "nonempty_patches": sum(bool(row.get("patch_nonempty")) for row in group),
            "official_evaluations_attempted": sum(bool(row.get("evaluation_attempted")) for row in group),
            "resolved": resolved,
            "unresolved_evaluated": sum(row.get("evaluation_attempted") and row.get("resolved") is False for row in group),
            "empty_patches": sum(not bool(row.get("patch_nonempty")) for row in group),
            "infrastructure_failures": infra,
            "agent_level_resolution_rate": _ratio(resolved, valid_agent_runs),
            "conditional_patch_correctness": _ratio(resolved, nonempty_evaluated),
        })
    output_root.mkdir(parents=True, exist_ok=True)
    _write_jsonl(output_root / "oracle_results.jsonl", combined)
    (output_root / "oracle_summary.json").write_text(json.dumps({
        "schema_version": 2,
        "provenance": collect_provenance(experiment_root, repo_root, swebench_harness_commit),
        "groups": summaries,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if summaries:
        with (output_root / "oracle_summary.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(summaries[0]))
            writer.writeheader()
            writer.writerows(summaries)
    combined_path = output_root / "rollout_oracle_combined.csv"
    if combined:
        with combined_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(combined[0]))
            writer.writeheader()
            writer.writerows(combined)
    return combined, summaries

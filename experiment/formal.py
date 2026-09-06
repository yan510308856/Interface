"""Formal G1/G2/G4 matrix planning, scheduling, and artifact handling."""

from __future__ import annotations

import hashlib
import json
import platform
import queue
import shutil
import subprocess
import sys
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from experiment.attack import AttackPlacement, load_placements
from experiment.attacks import get_attack
from experiment.model import Generation, Model
from experiment.runner import run_one
from experiment.task import Task, load_tasks


GRANULARITIES = ("G1", "G2", "G4")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_copy(value: Any) -> Any:
    return json.loads(json.dumps(value))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rooted(root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def _attack_ids(config: dict[str, Any]) -> list[str]:
    configured = config.get("attack_ids")
    if configured is None:
        configured = [config.get("active_attack")] if config.get("active_attack") else []
    result = [str(item) for item in configured if item]
    for attack_id in result:
        get_attack(attack_id)
    if len(result) != len(set(result)):
        raise ValueError("formal config contains duplicate attack_ids")
    return result


@dataclass(frozen=True)
class FormalRunSpec:
    task_id: str
    repo: str
    base_commit: str
    granularity: str
    condition: str
    attack_id: str | None
    rollout: int
    attack_index: int | None
    scheduler_index: int
    placement_id: str | None = None
    carrier_file: str | None = None

    @property
    def run_id(self) -> str:
        condition = "clean" if self.attack_id is None else f"attack{self.attack_index:02d}"
        return f"{self.task_id}-{self.granularity}-{condition}-r{self.rollout}"

    def as_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result.update({"run_id": self.run_id, "G": self.granularity})
        return result


def load_formal_tasks(
    config: dict[str, Any],
    repo_root: Path,
) -> tuple[list[Task], dict[tuple[str, str], AttackPlacement]]:
    task_config = config["task"]
    tasks = load_tasks(
        _rooted(repo_root, task_config["file"]),
        task_config["dataset"],
        metadata_dir=_rooted(repo_root, task_config["metadata_dir"]),
        source_root=_rooted(repo_root, task_config["source_root"]),
    )
    if task_config.get("require_prepared_sources"):
        missing = [task.instance_id for task in tasks if task.source_path is None]
        if missing:
            raise FileNotFoundError("missing prepared sources: " + ", ".join(missing))
    placement_file = task_config.get("placement_file")
    placements = load_placements(_rooted(repo_root, placement_file)) if placement_file else {}
    return tasks, placements


def build_formal_plan(
    config: dict[str, Any],
    repo_root: Path,
    *,
    task_filter: str | None = None,
) -> tuple[list[FormalRunSpec], list[Task], dict[tuple[str, str], AttackPlacement]]:
    interfaces = tuple(str(item) for item in config.get("interfaces", GRANULARITIES))
    if interfaces != GRANULARITIES:
        raise ValueError("formal matrix must use interfaces in the order G1, G2, G4")
    for condition, expected in zip(interfaces, (1, 2, 4)):
        configured = config.get("granularity", {}).get(condition, {})
        capacity = configured.get("max_ops_per_action") if isinstance(configured, dict) else configured
        if int(capacity) != expected:
            raise ValueError(f"{condition} must have max_ops_per_action={expected}")

    rollouts = config.get("rollouts", config.get("seeds"))
    if not rollouts:
        raise ValueError("formal config requires non-empty rollouts")
    rollouts = [int(item) for item in rollouts]
    if len(rollouts) != len(set(rollouts)) or any(item < 1 for item in rollouts):
        raise ValueError("rollouts must be unique positive integers")

    tasks, placements = load_formal_tasks(config, repo_root)
    tasks = [task for task in tasks if not task_filter or task.instance_id == task_filter]
    if task_filter and not tasks:
        raise ValueError(f"unknown formal task: {task_filter}")

    configured_conditions = tuple(config.get("conditions", ("clean", "attack")))
    if "clean" not in configured_conditions:
        raise ValueError("formal matrix requires clean condition")
    attack_ids = _attack_ids(config) if "attack" in configured_conditions else []
    if "attack" in configured_conditions and not attack_ids:
        raise ValueError("attack condition requires attack_ids or active_attack")
    if any(condition not in {"clean", "attack"} for condition in configured_conditions):
        raise ValueError("formal conditions must be clean and/or attack")

    plan: list[FormalRunSpec] = []
    scheduler_index = 0
    for task in tasks:
        for rollout in rollouts:
            blocks: list[tuple[str, str | None, int | None]] = []
            if "clean" in configured_conditions:
                blocks.append(("clean", None, None))
            if "attack" in configured_conditions:
                blocks.extend(("attack", attack_id, index) for index, attack_id in enumerate(attack_ids, 1))
            for condition, attack_id, attack_index in blocks:
                if attack_id and (task.instance_id, attack_id) not in placements:
                    raise ValueError(f"missing placement for {task.instance_id}/{attack_id}")
                placement = placements.get((task.instance_id, attack_id)) if attack_id else None
                for granularity in interfaces:
                    scheduler_index += 1
                    plan.append(FormalRunSpec(
                        task.instance_id, task.repo, task.base_commit, granularity,
                        condition, attack_id, rollout, attack_index, scheduler_index,
                        placement.placement_id if placement else None,
                        placement.selected_file if placement else None,
                    ))

    run_ids = [item.run_id for item in plan]
    if len(run_ids) != len(set(run_ids)):
        raise ValueError("formal plan contains duplicate run IDs")
    return plan, tasks, placements


class DeterministicFormalModel:
    """No-network model used only by the local formal pipeline dry-run."""

    def __init__(self) -> None:
        self.calls = 0

    def count_tokens(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None) -> int:
        return 1

    def generate(
        self,
        messages: list[dict[str, Any]],
        seed: int,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
        parallel_tool_calls: bool | None = None,
    ) -> Generation:
        self.calls += 1
        if self.calls == 1:
            capacity = 1
            if tools:
                capacity = tools[0]["function"]["parameters"]["properties"]["operations"].get("maxItems", 1)
            operations = [{"name": "git_diff", "arguments": {}} for _ in range(min(capacity, 2))]
            arguments = json.dumps({"operations": operations})
        else:
            arguments = json.dumps({"operations": [], "finish": "done"})
        return Generation(
            "", 1, 1, 0.0,
            [{
                "id": f"dry-call-{self.calls}",
                "type": "function",
                "function": {"name": "submit_action", "arguments": arguments},
            }],
        )


def _git_provenance(repo_root: Path) -> dict[str, Any]:
    def git(*args: str) -> str:
        return subprocess.check_output(["git", *args], cwd=repo_root, text=True).strip()

    return {
        "branch": git("branch", "--show-current"),
        "commit": git("rev-parse", "HEAD"),
        "status": git("status", "--porcelain"),
        "recorded_at": utc_now(),
    }


def prepare_experiment_root(
    output_root: Path,
    config: dict[str, Any],
    config_path: Path,
    permission_path: Path,
    repo_root: Path,
    plan: list[FormalRunSpec],
    tasks: list[Task],
    attack_ids: list[str],
    *,
    resume: bool,
    server_observed: dict[str, Any] | None = None,
) -> None:
    plan_path = output_root / "PLAN.json"
    if output_root.exists() and plan_path.exists():
        existing = json.loads(plan_path.read_text(encoding="utf-8"))
        existing_ids = [item["run_id"] for item in existing.get("runs", [])]
        if existing_ids != [item.run_id for item in plan]:
            raise ValueError("existing PLAN.json does not match the requested formal plan")
        metadata = _read_existing_metadata(output_root / "experiment_metadata.json")
        if metadata.get("config_sha256") != _sha256(config_path):
            raise ValueError("existing experiment config does not match --resume config")
        if metadata.get("permission_sha256") != _sha256(permission_path):
            raise ValueError("existing permission policy does not match --resume policy")
        if not resume:
            raise FileExistsError(f"{output_root} already contains a plan; use --resume")
        if server_observed is not None:
            server_path = output_root / "server_config.json"
            server = _read_existing_metadata(server_path)
            server["observed"] = server_observed
            _write_json(server_path, server)
        return
    if output_root.exists() and any(output_root.iterdir()):
        raise FileExistsError(f"refusing non-empty experiment root: {output_root}")

    output_root.mkdir(parents=True, exist_ok=True)
    for directory in ("configs", "tasks", "attacks", "runs", "summaries", "incomplete_attempts"):
        (output_root / directory).mkdir()
    _write_json(output_root / "PLAN.json", {
        "schema_version": "formal-granularity-v1",
        "experiment_id": config.get("experiment_id"),
        "run_count": len(plan),
        "schedule": "task x rollout blocks; G1/G2/G4 interleaved within each condition",
        "runs": [item.as_dict() for item in plan],
    })
    _write_json(output_root / "experiment_metadata.json", {
        "experiment_id": config.get("experiment_id"),
        "experiment_name": config.get("experiment_name"),
        "created_at": utc_now(),
        "formal_conditions": ["G1", "G2", "G4"],
        "conditions": config.get("conditions"),
        "rollouts": config.get("rollouts", config.get("seeds")),
        "task_count": len(tasks),
        "attack_ids": attack_ids,
        "network_policy": config.get("sandbox", {}).get("network"),
        "dry_run_is_not_real_data": True,
        "config_sha256": _sha256(config_path),
        "permission_sha256": _sha256(permission_path),
        "python": sys.version,
        "platform": platform.platform(),
    })
    server = dict(config.get("server", {}))
    server.setdefault("base_url", config.get("model", {}).get("base_url"))
    server.setdefault("model", config.get("model", {}).get("name"))
    server["observed"] = server_observed
    _write_json(output_root / "server_config.json", server)
    _write_json(output_root / "git_provenance.json", _git_provenance(repo_root))

    shutil.copy2(config_path, output_root / "configs" / config_path.name)
    shutil.copy2(permission_path, output_root / "configs" / permission_path.name)
    task_config = config["task"]
    shutil.copy2(_rooted(repo_root, task_config["file"]), output_root / "tasks" / Path(task_config["file"]).name)
    if task_config.get("placement_file"):
        shutil.copy2(
            _rooted(repo_root, task_config["placement_file"]),
            output_root / "attacks" / Path(task_config["placement_file"]).name,
        )
    _write_json(output_root / "tasks" / "task_manifest.json", {
        "tasks": [{
            "instance_id": task.instance_id,
            "repo": task.repo,
            "base_commit": task.base_commit,
            "metadata": task.metadata,
        } for task in tasks],
    })
    _write_json(output_root / "attacks" / "registry.json", [
        asdict(get_attack(attack_id)) for attack_id in attack_ids
    ])
    _write_json(output_root / "RUN_MANIFEST.json", {
        "schema_version": "formal-granularity-v1",
        "runs": [{"run_id": item.run_id, "scheduler_index": item.scheduler_index, "status": "pending"} for item in plan],
    })


def _read_existing_metadata(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _complete_run(run_dir: Path, spec: FormalRunSpec) -> bool:
    marker = run_dir / "COMPLETE.json"
    result_path = run_dir / "result.json"
    trajectory = run_dir / "trajectory.jsonl"
    metadata = run_dir / "metadata.json"
    if not all(path.is_file() for path in (marker, result_path, trajectory, metadata)):
        return False
    try:
        marker_value = json.loads(marker.read_text(encoding="utf-8"))
        result_value = json.loads(result_path.read_text(encoding="utf-8"))
        metadata_value = json.loads(metadata.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return all(
        value.get("run_id") == spec.run_id
        for value in (marker_value, result_value, metadata_value)
    ) and marker_value.get("status") == "completed"


def _quarantine_incomplete(output_root: Path, run_dir: Path, run_id: str) -> None:
    if not run_dir.exists():
        return
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = output_root / "incomplete_attempts" / f"{run_id}-{stamp}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(run_dir), str(destination))
    _write_json(destination / "INCOMPLETE.json", {
        "run_id": run_id,
        "status": "incomplete_previous_attempt",
        "quarantined_at": utc_now(),
    })


def _run_one_formal(
    spec: FormalRunSpec,
    task: Task,
    placements: dict[tuple[str, str], AttackPlacement],
    config: dict[str, Any],
    permission_policy: dict[str, Any],
    output_root: Path,
    worker_slot: int,
    dry_run: bool,
) -> dict[str, Any]:
    run_dir = output_root / "runs" / spec.run_id
    if _complete_run(run_dir, spec):
        return json.loads((run_dir / "result.json").read_text(encoding="utf-8")) | {"resume": "skipped_completed"}
    _quarantine_incomplete(output_root, run_dir, spec.run_id)

    started_at = utc_now()
    try:
        placement = placements.get((spec.task_id, spec.attack_id)) if spec.attack_id else None
        run_config = _json_copy(config)
        if spec.attack_id and run_config.get("attacks", {}).get(spec.attack_id):
            run_config["attack"] = run_config["attacks"][spec.attack_id]
        model = DeterministicFormalModel() if dry_run else Model(run_config["model"])
        result = run_one(
            task, spec.granularity, spec.condition, spec.rollout,
            run_config, permission_policy, model, run_dir,
            skip_evaluation=True, placement=placement, run_spec=spec,
        )
        ended_at = utc_now()
        result.update({
            "run_id": spec.run_id,
            "G": spec.granularity,
            "rollout": spec.rollout,
            "attack_id": spec.attack_id,
            "scheduler_index": spec.scheduler_index,
            "worker_slot": worker_slot,
            "run_started_at": started_at,
            "run_ended_at": ended_at,
            "status": "completed",
        })
        (run_dir / "patch.diff").write_text(result.get("final_patch", ""), encoding="utf-8")
        _write_json(run_dir / "result.json", result)
        _write_json(run_dir / "metadata.json", {
            "run_id": spec.run_id,
            "task_id": spec.task_id,
            "G": spec.granularity,
            "condition": spec.condition,
            "attack_id": spec.attack_id,
            "rollout": spec.rollout,
            "scheduler_index": spec.scheduler_index,
            "worker_slot": worker_slot,
            "run_started_at": started_at,
            "run_ended_at": ended_at,
            "model": run_config.get("model"),
            "budgets": run_config.get("budget"),
            "attack_metadata": result.get("attack_metadata"),
            "dry_run": dry_run,
        })
        _write_json(output_root / "runs" / spec.run_id / "COMPLETE.json", {
            "run_id": spec.run_id,
            "status": "completed",
            "completed_at": ended_at,
            "result_sha256": _sha256(run_dir / "result.json"),
            "trajectory_sha256": _sha256(run_dir / "trajectory.jsonl"),
        })
        return result
    except Exception as exc:  # worker isolation: other runs continue
        run_dir.mkdir(parents=True, exist_ok=True)
        _write_json(run_dir / "failure.json", {
            "run_id": spec.run_id,
            "status": "incomplete",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "run_started_at": started_at,
            "run_ended_at": utc_now(),
            "worker_slot": worker_slot,
        })
        return {
            "run_id": spec.run_id,
            "status": "incomplete",
            "error_type": type(exc).__name__,
            "error": str(exc),
        }


def _write_manifest(output_root: Path, plan: list[FormalRunSpec], results: list[dict[str, Any]]) -> None:
    by_id = {result.get("run_id"): result for result in results}
    _write_json(output_root / "RUN_MANIFEST.json", {
        "schema_version": "formal-granularity-v1",
        "updated_at": utc_now(),
        "runs": [{
            **spec.as_dict(),
            "status": by_id.get(spec.run_id, {}).get("status", "incomplete"),
            "resume": by_id.get(spec.run_id, {}).get("resume"),
        } for spec in plan],
    })


def run_formal_matrix(
    config: dict[str, Any],
    permission_policy: dict[str, Any],
    output_root: Path,
    repo_root: Path,
    config_path: Path,
    permission_path: Path,
    *,
    parallel: int = 3,
    resume: bool = False,
    dry_run: bool = False,
    task_filter: str | None = None,
    server_observed: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if not 1 <= parallel <= 3:
        raise ValueError("parallel must be between 1 and 3")
    plan, tasks, placements = build_formal_plan(config, repo_root, task_filter=task_filter)
    attack_ids = _attack_ids(config)
    prepare_experiment_root(
        output_root, config, config_path, permission_path, repo_root,
        plan, tasks, attack_ids, resume=resume, server_observed=server_observed,
    )
    task_by_id = {task.instance_id: task for task in tasks}
    work: queue.Queue[tuple[int, FormalRunSpec] | None] = queue.Queue()
    for index, spec in enumerate(plan):
        work.put((index, spec))
    for _ in range(parallel):
        work.put(None)
    results: list[dict[str, Any] | None] = [None] * len(plan)

    def worker(slot: int) -> None:
        while True:
            item = work.get()
            try:
                if item is None:
                    return
                index, spec = item
                results[index] = _run_one_formal(
                    spec, task_by_id[spec.task_id], placements, config,
                    permission_policy, output_root, slot, dry_run,
                )
            finally:
                work.task_done()

    threads = [threading.Thread(target=worker, args=(slot,), name=f"formal-worker-{slot}") for slot in range(1, parallel + 1)]
    for thread in threads:
        thread.start()
    work.join()
    for thread in threads:
        thread.join()
    completed = [result for result in results if result is not None]
    _write_manifest(output_root, plan, completed)
    _write_json(output_root / "experiment_metadata.json", {
        **json.loads((output_root / "experiment_metadata.json").read_text(encoding="utf-8")),
        "last_run_at": utc_now(),
        "parallel": parallel,
        "dry_run": dry_run,
        "completed_count": sum(result.get("status") == "completed" for result in completed),
        "incomplete_count": sum(result.get("status") != "completed" for result in completed),
    })
    return completed

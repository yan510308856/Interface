#!/usr/bin/env python3
"""Run the R1 ModelScope/Qwen feasibility smoke in isolated worker processes."""

from __future__ import annotations

import argparse
import contextlib
import copy
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiment import model_runtime  # noqa: E402


TOKEN_PATTERN = re.compile(r"\bms-[A-Za-z0-9_-]{8,}\b")
ATTEMPT_PATTERN = re.compile(r"^(.*?)(\d+)$")
PACKAGE_IMPORT_NAMES = {
    "modelscope": "modelscope",
    "modelscope-hub": "modelscope_hub",
    "transformers": "transformers",
    "accelerate": "accelerate",
    "torch": "torch",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def redact(text: str) -> str:
    """Remove token-shaped strings before persisting an error."""
    return TOKEN_PATTERN.sub("<redacted-modelscope-token>", text)


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n")
    temporary.replace(path)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    material = b"".join(canonical_bytes(row) for row in rows)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(material)
    temporary.replace(path)


def git_metadata() -> dict[str, Any]:
    def run(*arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *arguments],
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )

    revision = run("rev-parse", "HEAD")
    status = run("status", "--porcelain")
    return {
        "commit": revision.stdout.strip() if revision.returncode == 0 else None,
        "worktree_clean_at_start": status.returncode == 0 and not status.stdout.strip(),
        "status_error": redact(status.stderr.strip()) if status.returncode else None,
    }


def package_versions() -> dict[str, str | None]:
    versions: dict[str, str | None] = {}
    for package in PACKAGE_IMPORT_NAMES:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    return versions


def nvidia_smi() -> dict[str, Any]:
    command = [
        "nvidia-smi",
        "--query-gpu=name,uuid,memory.total,driver_version",
        "--format=csv,noheader,nounits",
    ]
    try:
        completed = subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"command": command, "exit_code": None, "error": redact(str(exc))}
    records = []
    for line in completed.stdout.splitlines():
        fields = [field.strip() for field in line.split(",")]
        if len(fields) == 4:
            records.append(
                {
                    "name": fields[0],
                    "uuid": fields[1],
                    "memory_total_mib": int(fields[2]) if fields[2].isdigit() else fields[2],
                    "driver_version": fields[3],
                }
            )
    return {
        "command": command,
        "exit_code": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": redact(completed.stderr.strip()),
        "gpus": records,
    }


def capture_environment(config: Mapping[str, Any]) -> dict[str, Any]:
    cache_name = config["cache_policy"]["environment_variable"]
    cache_value = os.environ.get(cache_name)
    disk_path = Path(cache_value).expanduser() if cache_value else Path.home()
    disk_path.mkdir(parents=True, exist_ok=True)
    usage = shutil.disk_usage(disk_path)
    colab_release_file = Path("/etc/colab-release")
    try:
        colab_package = importlib.metadata.version("google-colab")
    except importlib.metadata.PackageNotFoundError:
        colab_package = None
    colab_release_text = (
        colab_release_file.read_text(encoding="utf-8").strip()
        if colab_release_file.is_file()
        else None
    )
    gpu_report = nvidia_smi()
    environment: dict[str, Any] = {
        "captured_at": utc_now(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "python_executable": sys.executable,
        "packages": package_versions(),
        "nvidia_smi": gpu_report,
        "colab": {
            "release_tag": os.environ.get("COLAB_RELEASE_TAG"),
            "release_file": colab_release_text,
            "google_colab_package": colab_package,
        },
        "cache": {
            "configured_by": cache_name if cache_value else "modelscope-client-default",
            "path_recorded": str(disk_path.resolve()),
            "disk_total_mib": int(usage.total / (1024 * 1024)),
            "disk_free_mib": int(usage.free / (1024 * 1024)),
        },
    }
    try:
        import torch

        environment["torch"] = {
            "version": torch.__version__,
            "cuda_runtime": torch.version.cuda,
            "cuda_available": torch.cuda.is_available(),
            "cuda_device_count": torch.cuda.device_count(),
            "cudnn_version": torch.backends.cudnn.version(),
        }
    except Exception as exc:  # dependency failure belongs in the attempt bundle
        environment["torch"] = {"error": redact(str(exc))}
    gpu = gpu_report.get("gpus", [{}])[0] if len(gpu_report.get("gpus", [])) == 1 else {}
    torch_info = environment["torch"]
    environment["runtime_identity"] = {
        "colab_release": (
            environment["colab"]["release_tag"]
            or environment["colab"]["release_file"]
            or environment["colab"]["google_colab_package"]
        ),
        "python": environment["python"],
        "torch": environment["packages"].get("torch"),
        "cuda_runtime": torch_info.get("cuda_runtime"),
        "nvidia_driver": gpu.get("driver_version"),
        "gpu_name": gpu.get("name"),
        "gpu_memory_mib": gpu.get("memory_total_mib"),
    }
    return environment


def validate_package_versions(config: Mapping[str, Any], actual: Mapping[str, str | None]) -> None:
    for package, expected in config["packages"].items():
        found = actual.get(package)
        if expected == "record-from-colab-runtime" and package == "torch":
            if not found:
                raise RuntimeError("torch is not installed in the Colab runtime")
            continue
        if found != expected:
            raise RuntimeError(f"package version mismatch for {package}: expected {expected}, found {found}")


def validate_runtime_identity(config: Mapping[str, Any], actual: Mapping[str, Any]) -> None:
    """Require complete Colab identity and exact equality after the config is frozen."""
    missing = [name for name, value in actual.items() if value in {None, ""}]
    if missing:
        raise RuntimeError(f"incomplete Colab runtime identity: {missing}")
    if config["freeze_status"] == "frozen" and dict(config["runtime"]) != dict(actual):
        raise RuntimeError(
            f"Colab runtime differs from frozen config: expected {config['runtime']}, found {actual}"
        )


class FakeRuntime:
    """Small deterministic runtime used only by local tests and --fake."""

    def __init__(self) -> None:
        self.config: Mapping[str, Any] | None = None
        self.generations: list[dict[str, Any]] = []
        self.context: dict[str, Any] | None = None

    def load_model(self, config: Mapping[str, Any]) -> dict[str, Any]:
        model_runtime.validate_config(config)
        self.config = config
        return self.collect_metrics()

    def generate(self, messages: list[dict[str, str]], config: Mapping[str, Any]) -> dict[str, Any]:
        content = messages[-1]["content"]
        if "JSON object" in content:
            text = '{"type":"tool_call","operation":"read_file","arguments":{"path":"README.md","start_line":1,"end_line":5}}'
        elif "Python statement" in content:
            text = 'result = repo.read_file("README.md", start_line=1, end_line=5)'
        else:
            text = "R1_SMOKE_OK"
        input_digest = sha256_bytes(canonical_bytes(messages))
        result = {
            "text": text,
            "prompt_tokens": len(content.split()),
            "output_tokens": len(text.split()),
            "input_token_ids_sha256": input_digest,
            "output_token_ids_sha256": sha256_bytes(text.encode("utf-8")),
            "generation_seconds": 0.001,
            "tokens_per_second": 1000.0,
            "finish_reason": "eos",
        }
        self.generations.append(result)
        return result

    def run_context_probe(self, config: Mapping[str, Any]) -> dict[str, Any]:
        self.context = {
            "input_tokens": config["context_probe"]["input_tokens"],
            "output_tokens": config["context_probe"]["output_tokens"],
            "input_token_ids_sha256": sha256_bytes(b"fake-context-probe"),
            "generation_seconds": 0.001,
            "status": "PASS",
        }
        return self.context

    def collect_metrics(self) -> dict[str, Any]:
        return {
            "resolved_revision": "a" * 40,
            "tokenizer_revision": "a" * 40,
            "snapshot_path": "<fake>",
            "snapshot_digests": {
                "algorithm": "sha256",
                "files": [{"path": "fake.safetensors", "bytes": 1, "sha256": "b" * 64}],
                "snapshot_sha256": "c" * 64,
                "digest_seconds": 0.001,
            },
            "download_seconds": 0.001,
            "load_seconds": 0.001,
            "peak_gpu_memory_mib": 1.0,
            "reserved_gpu_memory_mib": 1.0,
            "hardware": {
                "gpu_name": "FAKE A100",
                "gpu_total_memory_mib": 80000,
                "gpu_compute_capability": "8.0",
                "cache_disk_free_mib_before_download": 100000,
            },
            "parameter_devices": ["cuda:0"],
            "generations": list(self.generations),
            "context_probe": self.context,
        }

    @staticmethod
    def parse_output(parser: str, text: str) -> dict[str, Any]:
        return model_runtime.parse_output(parser, text)

    @staticmethod
    def release_model() -> None:
        return None


def _validation(
    config: Mapping[str, Any],
    runtime_mode: str,
    environment: Mapping[str, Any],
    metrics: Mapping[str, Any],
    generations: list[dict[str, Any]],
) -> dict[str, Any]:
    checks: dict[str, dict[str, Any]] = {}

    def add(name: str, passed: bool, evidence: Any) -> None:
        checks[name] = {"status": "PASS" if passed else "FAIL", "evidence": evidence}

    resolved = metrics.get("resolved_revision")
    add("modelscope_source", config["provider"] == "modelscope", config["model_id"])
    add("immutable_revision", isinstance(resolved, str) and bool(model_runtime.SHA40.fullmatch(resolved)), resolved)
    digests = metrics.get("snapshot_digests", {})
    add("weight_digests", bool(digests.get("files")) and bool(digests.get("snapshot_sha256")), digests.get("snapshot_sha256"))
    hardware = metrics.get("hardware", {})
    add("a100_gpu", "a100" in str(hardware.get("gpu_name", "")).lower(), hardware)
    devices = metrics.get("parameter_devices", [])
    add("no_cpu_or_disk_offload", bool(devices) and all(str(value).startswith("cuda") for value in devices), devices)
    add("three_nonempty_outputs", len(generations) == 3 and all(row.get("output_tokens", 0) > 0 for row in generations), [row.get("prompt_id") for row in generations])
    add("syntax_parsers", len(generations) == 3 and all(row.get("parse", {}).get("ok") for row in generations), [row.get("parse") for row in generations])
    context = metrics.get("context_probe") or {}
    add(
        "planned_context",
        context.get("status") == "PASS" and context.get("input_tokens", 0) + context.get("output_tokens", 0) == config["context_limit"],
        context,
    )
    required_metrics = {
        "download_seconds",
        "load_seconds",
        "peak_gpu_memory_mib",
        "resolved_revision",
        "snapshot_digests",
        "context_probe",
    }
    add("metrics_complete", not (required_metrics - set(metrics)), sorted(required_metrics - set(metrics)))
    if runtime_mode == "real":
        versions = environment["packages"]
        package_ok = all(
            versions.get(name) == expected
            for name, expected in config["packages"].items()
            if expected != "record-from-colab-runtime"
        ) and bool(versions.get("torch"))
        add("package_versions", package_ok, versions)
    else:
        add("real_a100_evidence", False, "fake mode is local plumbing evidence only")
    failed = [name for name, result in checks.items() if result["status"] != "PASS"]
    overall = "PASS" if not failed else ("PASS_LOCAL_ONLY" if runtime_mode == "fake" and failed == ["real_a100_evidence"] else "REVISE")
    return {"schema_version": "r1-attempt-validation-v1", "overall": overall, "checks": checks, "blockers": failed}


def _artifact_digests(attempt_dir: Path) -> dict[str, Any]:
    entries: dict[str, Any] = {}
    for path in sorted(attempt_dir.iterdir()):
        if path.is_file() and path.name != "digests.json":
            data = path.read_bytes()
            entries[path.name] = {"bytes": len(data), "sha256": sha256_bytes(data)}
    identity = "".join(f"{name}\0{item['sha256']}\n" for name, item in entries.items())
    return {
        "schema_version": "r1-artifact-digests-v1",
        "algorithm": "sha256",
        "files": entries,
        "bundle_sha256": sha256_bytes(identity.encode("utf-8")),
    }


def run_attempt(
    config_path: Path,
    output_dir: Path,
    attempt_id: str,
    runtime_mode: str,
    runtime: Any | None = None,
) -> int:
    """Run one attempt and preserve a complete bundle on success or failure."""
    config = model_runtime.load_config(config_path)
    attempt_dir = output_dir / attempt_id
    if attempt_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing attempt: {attempt_dir}")
    attempt_dir.mkdir(parents=True)
    stdout_path = attempt_dir / "stdout.log"
    stderr_path = attempt_dir / "stderr.log"
    stdout_path.touch()
    stderr_path.touch()

    started = utc_now()
    config_sha256 = sha256_bytes(canonical_bytes(config))
    git = git_metadata()
    manifest: dict[str, Any] = {
        "schema_version": "r1-run-manifest-v1",
        "stage": "R1",
        "run_id": output_dir.name,
        "attempt_id": attempt_id,
        "runtime_mode": runtime_mode,
        "config_path": str(config_path),
        "config_sha256": config_sha256,
        "model_id": config["model_id"],
        "requested_revision": config["requested_revision"],
        "seed": config["seed"],
        "start_utc": started,
        "git": git,
    }
    environment = capture_environment(config)
    metrics: dict[str, Any] = {}
    generation_rows: list[dict[str, Any]] = []
    error: dict[str, Any] | None = None
    exit_code = 1
    selected_runtime = runtime or (FakeRuntime() if runtime_mode == "fake" else model_runtime)

    with stdout_path.open("w", encoding="utf-8") as stdout_handle, stderr_path.open("w", encoding="utf-8") as stderr_handle:
        with contextlib.redirect_stdout(stdout_handle), contextlib.redirect_stderr(stderr_handle):
            try:
                if runtime_mode == "real":
                    if not git.get("commit") or not git.get("worktree_clean_at_start"):
                        raise RuntimeError(
                            "formal A100 attempts require an exact commit and clean worktree"
                        )
                    validate_package_versions(config, environment["packages"])
                    validate_runtime_identity(config, environment["runtime_identity"])
                selected_runtime.load_model(config)
                for prompt in config["prompts"]:
                    result = selected_runtime.generate(prompt["messages"], config)
                    parsed = selected_runtime.parse_output(prompt["parser"], result["text"])
                    generation_rows.append(
                        {
                            "prompt_id": prompt["id"],
                            "parser": prompt["parser"],
                            **result,
                            "parse": parsed,
                        }
                    )
                selected_runtime.run_context_probe(config)
                metrics = selected_runtime.collect_metrics()
                metrics["generations"] = generation_rows
                validation = _validation(config, runtime_mode, environment, metrics, generation_rows)
                exit_code = 0 if validation["overall"] in {"PASS", "PASS_LOCAL_ONLY"} else 1
            except Exception as exc:
                error = {
                    "class": type(exc).__name__,
                    "message": redact(str(exc)),
                    "traceback": redact(traceback.format_exc()),
                }
                print(error["traceback"], file=stderr_handle)
                validation = {
                    "schema_version": "r1-attempt-validation-v1",
                    "overall": "REVISE",
                    "checks": {"attempt_completed": {"status": "FAIL", "evidence": error["message"]}},
                    "blockers": ["attempt_completed"],
                }
            finally:
                try:
                    selected_runtime.release_model()
                except Exception as release_exc:
                    print(f"release warning: {redact(str(release_exc))}", file=stderr_handle)

    manifest.update(
        {
            "end_utc": utc_now(),
            "exit_code": exit_code,
            "resolved_revision": metrics.get("resolved_revision"),
            "tokenizer_revision": metrics.get("tokenizer_revision"),
            "snapshot_sha256": metrics.get("snapshot_digests", {}).get("snapshot_sha256"),
            "error": error,
        }
    )
    atomic_json(attempt_dir / "run_manifest.json", manifest)
    atomic_json(attempt_dir / "environment.json", environment)
    atomic_json(attempt_dir / "metrics.json", metrics)
    atomic_json(attempt_dir / "validation.json", validation)
    write_jsonl(attempt_dir / "generations.jsonl", generation_rows)
    atomic_json(attempt_dir / "digests.json", _artifact_digests(attempt_dir))
    print(f"{attempt_id}: {validation['overall']} -> {attempt_dir}")
    return exit_code


def increment_attempt(attempt_id: str, offset: int) -> str:
    match = ATTEMPT_PATTERN.fullmatch(attempt_id)
    if not match:
        if offset:
            raise ValueError("multiple processes require an attempt ID ending in digits")
        return attempt_id
    prefix, number = match.groups()
    return f"{prefix}{int(number) + offset:0{len(number)}d}"


def compare_attempts(config: Mapping[str, Any], output_dir: Path, attempts: list[str]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    bundles = []
    for attempt in attempts:
        attempt_dir = output_dir / attempt
        bundles.append(
            {
                "attempt": attempt,
                "manifest": json.loads((attempt_dir / "run_manifest.json").read_text(encoding="utf-8")),
                "environment": json.loads((attempt_dir / "environment.json").read_text(encoding="utf-8")),
                "metrics": json.loads((attempt_dir / "metrics.json").read_text(encoding="utf-8")),
                "validation": json.loads((attempt_dir / "validation.json").read_text(encoding="utf-8")),
            }
        )
    comparisons: dict[str, Any] = {}

    def equal(name: str, values: list[Any]) -> None:
        comparisons[name] = {"equal": len({json.dumps(value, sort_keys=True) for value in values}) == 1, "values": values}

    equal("config_sha256", [item["manifest"].get("config_sha256") for item in bundles])
    equal("resolved_revision", [item["manifest"].get("resolved_revision") for item in bundles])
    equal("tokenizer_revision", [item["manifest"].get("tokenizer_revision") for item in bundles])
    equal("snapshot_sha256", [item["manifest"].get("snapshot_sha256") for item in bundles])
    equal("runtime_identity", [item["environment"].get("runtime_identity") for item in bundles])
    equal(
        "input_token_ids",
        [[row.get("input_token_ids_sha256") for row in item["metrics"].get("generations", [])] for item in bundles],
    )
    equal(
        "context_probe_input_ids",
        [item["metrics"].get("context_probe", {}).get("input_token_ids_sha256") for item in bundles],
    )
    attempts_pass = all(item["validation"].get("overall") == "PASS" for item in bundles)
    comparisons_pass = all(item["equal"] for item in comparisons.values())
    frozen = config["freeze_status"] == "frozen"
    status = "PASS" if attempts_pass and comparisons_pass and frozen else "REVISE"
    blockers = []
    if not attempts_pass:
        blockers.append("one_or_more_attempts_failed")
    if not comparisons_pass:
        blockers.append("two_process_identity_mismatch")
    if not frozen:
        blockers.append("tracked_model_config_not_frozen")
    summary = {
        "schema_version": "r1-two-process-validation-v1",
        "status": status,
        "attempts": attempts,
        "comparisons": comparisons,
        "blockers": blockers,
    }

    candidate: dict[str, Any] | None = None
    revisions = [item["manifest"].get("resolved_revision") for item in bundles]
    if not frozen and len(set(revisions)) == 1 and revisions[0] and model_runtime.SHA40.fullmatch(revisions[0]):
        candidate = copy.deepcopy(dict(config))
        candidate["resolved_revision"] = revisions[0]
        candidate["tokenizer_revision"] = revisions[0]
        candidate["freeze_status"] = "frozen"
        torch_versions = [item["environment"]["packages"].get("torch") for item in bundles]
        if len(set(torch_versions)) == 1 and torch_versions[0]:
            candidate["packages"]["torch"] = torch_versions[0]
        runtime_identities = [item["environment"].get("runtime_identity") for item in bundles]
        if len({json.dumps(value, sort_keys=True) for value in runtime_identities}) == 1:
            candidate["runtime"] = runtime_identities[0]
        candidate["candidate_evidence"] = {
            "run_id": output_dir.name,
            "attempts": attempts,
            "snapshot_sha256": bundles[0]["manifest"].get("snapshot_sha256"),
        }
    return summary, candidate


def run_workers(args: argparse.Namespace, config: Mapping[str, Any]) -> int:
    attempts = [increment_attempt(args.attempt_id, offset) for offset in range(args.process_count)]
    existing = [attempt for attempt in attempts if (args.output_dir / attempt).exists()]
    if existing:
        print(
            f"refusing to overwrite existing attempts: {existing}; choose a new run directory",
            file=sys.stderr,
        )
        return 2
    for attempt in attempts:
        command = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--config",
            str(args.config.resolve()),
            "--output-dir",
            str(args.output_dir.resolve()),
            "--attempt-id",
            attempt,
            "--runtime",
            args.runtime,
            "--worker",
        ]
        completed = subprocess.run(command, cwd=ROOT, check=False)
        if completed.returncode != 0:
            print(f"worker {attempt} failed; preserved its bundle", file=sys.stderr)
    summary, candidate = compare_attempts(config, args.output_dir, attempts)
    if len(attempts) != 2:
        summary["status"] = "REVISE"
        summary["blockers"].append("two_separate_processes_required")
    atomic_json(args.output_dir / "two_process_validation.json", summary)
    if candidate is not None:
        atomic_json(args.output_dir / "resolved_model_config.json", candidate)
        print(
            "A100 evidence produced a candidate frozen config. Review resolved_model_config.json, "
            "update the tracked model.yaml, then rerun both processes."
        )
    print(f"two-process R1 status: {summary['status']} -> {args.output_dir}")
    return 0 if summary["status"] == "PASS" else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--attempt-id", default="attempt-00")
    parser.add_argument("--process-count", type=int, choices=(1, 2), default=1)
    parser.add_argument("--runtime", choices=("real", "fake"), default="real")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        config = model_runtime.load_config(args.config)
    except model_runtime.ConfigError as exc:
        print(f"invalid config: {exc}", file=sys.stderr)
        return 2
    if args.dry_run:
        print(
            json.dumps(
                {
                    "status": "DRY_RUN_OK",
                    "model_id": config["model_id"],
                    "provider": config["provider"],
                    "freeze_status": config["freeze_status"],
                    "process_count_requested": args.process_count,
                    "prompts": [item["id"] for item in config["prompts"]],
                    "context_limit": config["context_limit"],
                    "note": "No model was downloaded or loaded.",
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.output_dir is None:
        print("--output-dir is required unless --dry-run is used", file=sys.stderr)
        return 2
    if args.worker:
        return run_attempt(args.config, args.output_dir, args.attempt_id, args.runtime)
    return run_workers(args, config)


if __name__ == "__main__":
    raise SystemExit(main())

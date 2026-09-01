"""Minimal ModelScope-backed model runtime for the R1 A100 feasibility gate.

The module deliberately has one active model per process. R1 uses separate worker
processes, so a second smoke cannot accidentally reuse the first process's model.
Heavy dependencies are imported lazily; local config tests need only Python's
standard library.
"""

from __future__ import annotations

import ast
import contextlib
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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Sequence


SHA40 = re.compile(r"^[0-9a-f]{40}$")
REQUIRED_TOP_LEVEL = {
    "schema_version",
    "provider",
    "model_id",
    "repository_url",
    "requested_revision",
    "resolved_revision",
    "tokenizer_revision",
    "freeze_status",
    "engine",
    "packages",
    "runtime",
    "context_limit",
    "max_output_tokens",
    "context_probe",
    "sampling",
    "seed",
    "hardware",
    "cache_policy",
    "prompts",
}
FLOATING_REVISIONS = {"main", "master", "latest", "dev"}
KEY_SNAPSHOT_FILES = {
    "config.json",
    "generation_config.json",
    "model.safetensors.index.json",
    "tokenizer.json",
    "tokenizer_config.json",
}

_ACTIVE: dict[str, Any] | None = None


class ConfigError(ValueError):
    """Raised when the frozen model config is incomplete or inconsistent."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _progress(message: str) -> None:
    print(f"[{_utc_now()}] [R1] {message}", file=sys.stdout, flush=True)


def _format_gib(byte_count: int) -> str:
    return f"{byte_count / (1024 ** 3):.2f} GiB"


def _directory_size(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for candidate in path.rglob("*"):
        try:
            if candidate.is_file():
                total += candidate.stat().st_size
        except OSError:
            continue
    return total


@contextlib.contextmanager
def _heartbeat(
    label: str,
    details: Callable[[], str],
    *,
    interval_seconds: float = 30.0,
) -> Iterator[None]:
    """Emit progress for blocking third-party calls that may otherwise be silent."""
    started = time.monotonic()
    stopped = threading.Event()
    _progress(f"{label} started; {details()}")

    def report() -> None:
        while not stopped.wait(interval_seconds):
            elapsed = int(time.monotonic() - started)
            _progress(f"{label} still running; elapsed={elapsed}s; {details()}")

    reporter = threading.Thread(target=report, name="r1-progress", daemon=True)
    reporter.start()
    try:
        yield
    finally:
        stopped.set()
        reporter.join(timeout=1)
        elapsed = time.monotonic() - started
        _progress(f"{label} finished; elapsed={elapsed:.1f}s; {details()}")


def load_config(path: str | Path) -> dict[str, Any]:
    """Load JSON-syntax YAML and validate the R1 contract."""
    config_path = Path(path)
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"cannot load model config {config_path}: {exc}") from exc
    validate_config(config)
    return config


def validate_config(config: Mapping[str, Any]) -> None:
    """Reject missing, unsafe, floating-frozen, or internally inconsistent values."""
    missing = sorted(REQUIRED_TOP_LEVEL - set(config))
    if missing:
        raise ConfigError(f"missing model config fields: {missing}")
    if config["schema_version"] != "model-config-v0.1":
        raise ConfigError("unsupported model config schema_version")
    if config["provider"] != "modelscope":
        raise ConfigError("R1 model provider must be modelscope")
    if config["model_id"] != "Qwen/Qwen3-Coder-30B-A3B-Instruct":
        raise ConfigError("model_id differs from the fixed research design")
    if not str(config["repository_url"]).startswith("https://www.modelscope.cn/"):
        raise ConfigError("repository_url must use the ModelScope host")
    requested = config["requested_revision"]
    if not isinstance(requested, str) or not requested.startswith("refs/"):
        raise ConfigError("requested_revision must be an explicit Git ref")
    resolved = config["resolved_revision"]
    tokenizer_revision = config["tokenizer_revision"]
    for name, value in (
        ("resolved_revision", resolved),
        ("tokenizer_revision", tokenizer_revision),
    ):
        if value is not None and not SHA40.fullmatch(value):
            raise ConfigError(f"{name} must be null before A100 or a full commit SHA")
    if (resolved is None) != (tokenizer_revision is None):
        raise ConfigError("model and tokenizer revisions must be frozen together")
    if resolved is not None and resolved != tokenizer_revision:
        raise ConfigError("model and tokenizer revisions must be identical")
    if resolved and resolved.lower() in FLOATING_REVISIONS:
        raise ConfigError("resolved revision cannot be floating")
    expected_freeze = "frozen" if resolved else "pending_a100"
    if config["freeze_status"] != expected_freeze:
        raise ConfigError(f"freeze_status must be {expected_freeze!r}")

    engine = config["engine"]
    required_engine = {
        "name": "transformers",
        "dtype": "bfloat16",
        "device": "cuda:0",
        "trust_remote_code": False,
        "quantization": "none",
        "allow_cpu_offload": False,
        "allow_disk_offload": False,
    }
    for key, expected in required_engine.items():
        if engine.get(key) != expected:
            raise ConfigError(f"engine.{key} must be {expected!r}")
    if engine.get("version") != config["packages"].get("transformers"):
        raise ConfigError("engine and package Transformers versions differ")
    torch_version = config["packages"].get("torch")
    if resolved is None and torch_version != "record-from-colab-runtime":
        raise ConfigError("pending config must record torch from the Colab runtime")
    if resolved is not None and (
        not isinstance(torch_version, str)
        or torch_version == "record-from-colab-runtime"
    ):
        raise ConfigError("frozen config must contain the exact Colab torch version")
    runtime = config["runtime"]
    required_runtime = {
        "colab_release",
        "python",
        "torch",
        "cuda_runtime",
        "nvidia_driver",
        "gpu_name",
        "gpu_memory_mib",
    }
    if set(runtime) != required_runtime:
        raise ConfigError("runtime identity fields are incomplete")
    placeholder = "record-from-colab-runtime"
    if resolved is None and any(value != placeholder for value in runtime.values()):
        raise ConfigError("pending config must record all runtime identity on Colab")
    if resolved is not None and any(
        not isinstance(value, (str, int)) or value == placeholder or value == ""
        for value in runtime.values()
    ):
        raise ConfigError("frozen config must contain exact Colab runtime values")

    context_limit = config["context_limit"]
    max_output = config["max_output_tokens"]
    probe = config["context_probe"]
    if not isinstance(context_limit, int) or context_limit < 1024:
        raise ConfigError("context_limit must be an integer >= 1024")
    if not isinstance(max_output, int) or not 1 <= max_output < context_limit:
        raise ConfigError("max_output_tokens must fit within context_limit")
    if probe.get("input_tokens", 0) + probe.get("output_tokens", 0) != context_limit:
        raise ConfigError("context probe must exercise the complete planned context")
    sampling = config["sampling"]
    if sampling != {"do_sample": False, "temperature": None, "top_p": None}:
        raise ConfigError("R1 uses deterministic greedy decoding")
    if not isinstance(config["seed"], int):
        raise ConfigError("seed must be an integer")

    prompts = config["prompts"]
    expected_parsers = {"plain": "nonempty", "atomic_json": "atomic_json", "restricted_python": "python_ast"}
    if not isinstance(prompts, list) or len(prompts) != 3:
        raise ConfigError("R1 requires exactly three fixed prompts")
    found = {item.get("id"): item.get("parser") for item in prompts}
    if found != expected_parsers:
        raise ConfigError("R1 prompt IDs or parsers differ from the fixed set")
    for prompt in prompts:
        messages = prompt.get("messages")
        if not isinstance(messages, list) or not messages:
            raise ConfigError(f"prompt {prompt.get('id')!r} has no messages")
        for message in messages:
            if set(message) != {"role", "content"} or message["role"] not in {"system", "user", "assistant"}:
                raise ConfigError(f"invalid message in prompt {prompt.get('id')!r}")
            if not isinstance(message["content"], str) or not message["content"]:
                raise ConfigError(f"empty message in prompt {prompt.get('id')!r}")


def collect_colab_runtime_identity() -> dict[str, Any]:
    """Collect the exact frozen runtime fields before an R6-P Qwen load."""
    import torch

    completed = subprocess.run(
        [
            "nvidia-smi", "--query-gpu=name,memory.total,driver_version",
            "--format=csv,noheader,nounits",
        ],
        check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=30,
    )
    rows = [row.strip() for row in completed.stdout.splitlines() if row.strip()]
    if completed.returncode or len(rows) != 1:
        raise RuntimeError("exactly one NVIDIA GPU is required")
    parts = [part.strip() for part in rows[0].split(",")]
    if len(parts) != 3:
        raise RuntimeError("unexpected nvidia-smi identity output")
    release_file = Path("/etc/colab-release")
    colab_release = os.environ.get("COLAB_RELEASE_TAG")
    if not colab_release and release_file.is_file():
        colab_release = release_file.read_text(encoding="utf-8").strip()
    if not colab_release:
        try:
            colab_release = importlib.metadata.version("google-colab")
        except importlib.metadata.PackageNotFoundError:
            colab_release = None
    return {
        "colab_release": colab_release,
        "python": platform.python_version(),
        "torch": torch.__version__,
        "cuda_runtime": torch.version.cuda,
        "nvidia_driver": parts[2],
        "gpu_name": parts[0],
        "gpu_memory_mib": int(parts[1]),
    }


def validate_colab_runtime(
    config: Mapping[str, Any], *, allow_colab_release_drift: bool = False
) -> dict[str, Any]:
    """Validate R1 identity, optionally allowing only the Colab release label."""
    actual_packages: dict[str, str | None] = {}
    for package, expected in config["packages"].items():
        try:
            actual = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            actual = None
        actual_packages[package] = actual
        if actual != expected:
            raise RuntimeError(
                f"package version mismatch for {package}: expected {expected}, found {actual}"
            )
    identity = collect_colab_runtime_identity()
    drift = {
        name: {"expected": config["runtime"].get(name), "actual": identity.get(name)}
        for name in sorted(set(config["runtime"]) | set(identity))
        if config["runtime"].get(name) != identity.get(name)
    }
    release_only = set(drift) == {"colab_release"}
    if drift and not (allow_colab_release_drift and release_only):
        raise RuntimeError(
            f"Colab runtime differs from R1 freeze: expected {config['runtime']}, found {identity}"
        )
    return {
        "packages": actual_packages,
        "runtime": identity,
        "compatibility": "colab_release_drift_allowed" if drift else "exact_r1_match",
        "drift": drift,
    }


def resolve_modelscope_revision(config: Mapping[str, Any]) -> str:
    """Resolve the configured ModelScope Git ref to an immutable commit SHA."""
    resolved = config.get("resolved_revision")
    if isinstance(resolved, str) and SHA40.fullmatch(resolved):
        return resolved
    _progress(f"resolving immutable ModelScope revision for {config['model_id']}")
    completed = subprocess.run(
        ["git", "ls-remote", config["repository_url"], config["requested_revision"]],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=120,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip().splitlines()[-1:] or ["unknown git error"]
        raise RuntimeError(f"cannot resolve ModelScope revision: {detail[0]}")
    rows = [line.split() for line in completed.stdout.splitlines() if line.strip()]
    matches = [row[0] for row in rows if len(row) == 2 and row[1] == config["requested_revision"]]
    if len(matches) != 1 or not SHA40.fullmatch(matches[0]):
        raise RuntimeError("ModelScope ref did not resolve to exactly one full commit SHA")
    return matches[0]


def _cache_dir(config: Mapping[str, Any]) -> str | None:
    env_name = config["cache_policy"]["environment_variable"]
    value = os.environ.get(env_name)
    return value if value else None


def _check_hardware(config: Mapping[str, Any], torch: Any) -> dict[str, Any]:
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError("R1 requires exactly one CUDA GPU")
    properties = torch.cuda.get_device_properties(0)
    total_mib = int(properties.total_memory / (1024 * 1024))
    requirement = config["hardware"]
    if requirement["required_gpu_name_contains"].lower() not in properties.name.lower():
        raise RuntimeError(f"R1 requires an A100; detected {properties.name!r}")
    if total_mib < requirement["minimum_gpu_memory_mib"]:
        raise RuntimeError(
            f"unquantized BF16 model requires an 80 GB-class A100; detected {total_mib} MiB"
        )
    cache = _cache_dir(config)
    disk_root = Path(cache).expanduser() if cache else Path.home()
    disk_root.mkdir(parents=True, exist_ok=True)
    free_mib = int(shutil.disk_usage(disk_root).free / (1024 * 1024))
    if free_mib < requirement["minimum_cache_disk_free_mib"]:
        raise RuntimeError(
            f"insufficient cache disk: need {requirement['minimum_cache_disk_free_mib']} MiB, found {free_mib} MiB"
        )
    return {
        "gpu_name": properties.name,
        "gpu_total_memory_mib": total_mib,
        "gpu_compute_capability": f"{properties.major}.{properties.minor}",
        "cache_disk_free_mib_before_download": free_mib,
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def digest_snapshot(snapshot: str | Path) -> dict[str, Any]:
    """Hash every weight shard plus key tokenizer/config files."""
    root = Path(snapshot)
    files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and (path.suffix == ".safetensors" or path.name in KEY_SNAPSHOT_FILES)
    )
    if not files or not any(path.suffix == ".safetensors" for path in files):
        raise RuntimeError("downloaded snapshot has no safetensors weight shards")
    started = time.monotonic()
    entries = []
    total_bytes = sum(path.stat().st_size for path in files)
    _progress(
        f"snapshot hashing started; files={len(files)}, total={_format_gib(total_bytes)}"
    )
    for index, path in enumerate(files, start=1):
        size = path.stat().st_size
        _progress(
            f"hashing file {index}/{len(files)}: {path.name} ({_format_gib(size)})"
        )
        entries.append(
            {
                "path": path.relative_to(root).as_posix(),
                "bytes": size,
                "sha256": _sha256_file(path),
            }
        )
    identity = "".join(f"{item['path']}\0{item['bytes']}\0{item['sha256']}\n" for item in entries)
    result = {
        "algorithm": "sha256",
        "files": entries,
        "snapshot_sha256": hashlib.sha256(identity.encode("utf-8")).hexdigest(),
        "digest_seconds": round(time.monotonic() - started, 6),
    }
    _progress(f"snapshot hashing finished; seconds={result['digest_seconds']}")
    return result


def prefetch_snapshot(
    config: Mapping[str, Any],
    *,
    downloader: Callable[..., str] | None = None,
) -> dict[str, Any]:
    """Download one immutable ModelScope snapshot without requiring a GPU."""
    validate_config(config)
    if downloader is None:
        from modelscope import snapshot_download

        downloader = snapshot_download

    revision = resolve_modelscope_revision(config)
    _progress(f"resolved ModelScope revision: {revision}")
    cache_path = Path(_cache_dir(config) or Path.home()).expanduser()
    cache_path.mkdir(parents=True, exist_ok=True)

    def download_details() -> str:
        usage = shutil.disk_usage(cache_path)
        return (
            f"cache={_format_gib(_directory_size(cache_path))}, "
            f"disk_free={_format_gib(usage.free)}"
        )

    download_started = time.monotonic()
    with _heartbeat("ModelScope snapshot download", download_details):
        snapshot = downloader(
            model_id=config["model_id"],
            revision=revision,
            cache_dir=_cache_dir(config),
        )
    return {
        "resolved_revision": revision,
        "snapshot_path": str(Path(snapshot).resolve()),
        "download_seconds": round(time.monotonic() - download_started, 6),
        "cache_bytes": _directory_size(cache_path),
    }


def load_model(config: Mapping[str, Any]) -> dict[str, Any]:
    """Download from ModelScope and load one model onto CUDA without offload."""
    global _ACTIVE
    validate_config(config)
    if _ACTIVE is not None:
        raise RuntimeError("one model is already active in this process")

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    hardware = _check_hardware(config, torch)
    _progress(
        f"hardware accepted: {hardware['gpu_name']}, "
        f"GPU={hardware['gpu_total_memory_mib']} MiB, "
        f"cache_free={hardware['cache_disk_free_mib_before_download']} MiB"
    )
    torch.manual_seed(config["seed"])
    torch.cuda.manual_seed_all(config["seed"])
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats(0)

    prefetched = prefetch_snapshot(config)
    revision = prefetched["resolved_revision"]
    snapshot = prefetched["snapshot_path"]
    download_seconds = prefetched["download_seconds"]
    snapshot_digests = digest_snapshot(snapshot)

    def load_details() -> str:
        return (
            f"GPU allocated={torch.cuda.memory_allocated(0) / (1024 ** 3):.2f} GiB, "
            f"reserved={torch.cuda.memory_reserved(0) / (1024 ** 3):.2f} GiB"
        )

    load_started = time.monotonic()
    with _heartbeat("tokenizer and BF16 model load", load_details):
        tokenizer = AutoTokenizer.from_pretrained(
            snapshot,
            local_files_only=True,
            trust_remote_code=False,
        )
        model = AutoModelForCausalLM.from_pretrained(
            snapshot,
            local_files_only=True,
            trust_remote_code=False,
            dtype=torch.bfloat16,
            device_map={"": 0},
            low_cpu_mem_usage=True,
            attn_implementation=config["engine"]["attention_implementation"],
        )
        model.eval()
        torch.cuda.synchronize()
    load_seconds = time.monotonic() - load_started

    placements = sorted({str(parameter.device) for parameter in model.parameters()})
    if not placements or any(not placement.startswith("cuda") for placement in placements):
        raise RuntimeError(f"CPU/disk offload detected in parameter placements: {placements}")
    hf_map = getattr(model, "hf_device_map", None)
    if isinstance(hf_map, dict):
        invalid = [value for value in hf_map.values() if str(value) not in {"0", "cuda", "cuda:0"}]
        if invalid:
            raise RuntimeError(f"CPU/disk offload detected in hf_device_map: {invalid}")

    _ACTIVE = {
        "model": model,
        "tokenizer": tokenizer,
        "torch": torch,
        "config": dict(config),
        "resolved_revision": revision,
        "tokenizer_revision": revision,
        "snapshot_path": str(Path(snapshot).resolve()),
        "snapshot_digests": snapshot_digests,
        "download_seconds": round(download_seconds, 6),
        "load_seconds": round(load_seconds, 6),
        "hardware": hardware,
        "parameter_devices": placements,
        "generations": [],
        "context_probe": None,
    }
    return collect_metrics()


def _input_digest(values: Sequence[int]) -> str:
    material = ",".join(str(value) for value in values).encode("ascii")
    return hashlib.sha256(material).hexdigest()


def generate(messages: Sequence[Mapping[str, str]], config: Mapping[str, Any]) -> dict[str, Any]:
    """Generate one deterministic response with the active model."""
    if _ACTIVE is None:
        raise RuntimeError("load_model(config) must be called before generate")
    validate_config(config)
    model = _ACTIVE["model"]
    tokenizer = _ACTIVE["tokenizer"]
    torch = _ACTIVE["torch"]

    rendered = tokenizer.apply_chat_template(
        list(messages), tokenize=False, add_generation_prompt=True
    )
    encoded = tokenizer(rendered, return_tensors="pt", add_special_tokens=False)
    input_ids = encoded["input_ids"]
    prompt_tokens = int(input_ids.shape[-1])
    if prompt_tokens + config["max_output_tokens"] > config["context_limit"]:
        raise RuntimeError("fixed prompt plus output budget exceeds planned context")
    encoded = {key: value.to("cuda:0") for key, value in encoded.items()}
    torch.cuda.synchronize()
    started = time.monotonic()
    with torch.inference_mode():
        output = model.generate(
            **encoded,
            max_new_tokens=config["max_output_tokens"],
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    torch.cuda.synchronize()
    seconds = time.monotonic() - started
    new_ids = output[0, prompt_tokens:]
    output_ids = [int(value) for value in new_ids.tolist()]
    text = tokenizer.decode(new_ids, skip_special_tokens=True)
    eos_id = tokenizer.eos_token_id
    result = {
        "text": text,
        "prompt_tokens": prompt_tokens,
        "output_tokens": len(output_ids),
        "input_token_ids_sha256": _input_digest([int(value) for value in input_ids[0].tolist()]),
        "output_token_ids_sha256": _input_digest(output_ids),
        "generation_seconds": round(seconds, 6),
        "tokens_per_second": round(len(output_ids) / seconds, 6) if seconds else None,
        "finish_reason": "eos" if eos_id in output_ids else "length",
    }
    _ACTIVE["generations"].append(result)
    return result


def run_context_probe(config: Mapping[str, Any]) -> dict[str, Any]:
    """Exercise the complete planned context with one generated token."""
    if _ACTIVE is None:
        raise RuntimeError("load_model(config) must be called before the context probe")
    tokenizer = _ACTIVE["tokenizer"]
    model = _ACTIVE["model"]
    torch = _ACTIVE["torch"]
    target = config["context_probe"]["input_tokens"]
    seed_ids = tokenizer.encode(" context", add_special_tokens=False)
    if not seed_ids:
        raise RuntimeError("tokenizer produced no context-probe seed token")
    ids = (seed_ids * ((target // len(seed_ids)) + 1))[:target]
    input_ids = torch.tensor([ids], dtype=torch.long, device="cuda:0")
    attention_mask = torch.ones_like(input_ids)
    torch.cuda.synchronize()
    started = time.monotonic()
    with torch.inference_mode():
        output = model.generate(
            input_ids=input_ids,
            attention_mask=attention_mask,
            max_new_tokens=config["context_probe"]["output_tokens"],
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    torch.cuda.synchronize()
    result = {
        "input_tokens": target,
        "output_tokens": int(output.shape[-1] - target),
        "input_token_ids_sha256": _input_digest(ids),
        "generation_seconds": round(time.monotonic() - started, 6),
        "status": "PASS",
    }
    _ACTIVE["context_probe"] = result
    return result


def collect_metrics() -> dict[str, Any]:
    """Return provenance and current CUDA metrics for the active runtime."""
    if _ACTIVE is None:
        raise RuntimeError("no active model")
    torch = _ACTIVE["torch"]
    return {
        "resolved_revision": _ACTIVE["resolved_revision"],
        "tokenizer_revision": _ACTIVE["tokenizer_revision"],
        "snapshot_path": _ACTIVE["snapshot_path"],
        "snapshot_digests": _ACTIVE["snapshot_digests"],
        "download_seconds": _ACTIVE["download_seconds"],
        "load_seconds": _ACTIVE["load_seconds"],
        "peak_gpu_memory_mib": round(torch.cuda.max_memory_allocated(0) / (1024 * 1024), 3),
        "reserved_gpu_memory_mib": round(torch.cuda.max_memory_reserved(0) / (1024 * 1024), 3),
        "hardware": _ACTIVE["hardware"],
        "parameter_devices": _ACTIVE["parameter_devices"],
        "generations": list(_ACTIVE["generations"]),
        "context_probe": _ACTIVE["context_probe"],
    }


def parse_output(parser: str, text: str) -> dict[str, Any]:
    """Apply the simple syntax-level R1 output parsers."""
    stripped = text.strip()
    if not stripped:
        return {"ok": False, "error": "empty_output"}
    if parser == "nonempty":
        return {"ok": True, "kind": "nonempty"}
    if parser == "atomic_json":
        try:
            value = json.loads(stripped)
        except json.JSONDecodeError as exc:
            return {"ok": False, "error": f"invalid_json:{exc.msg}"}
        expected = {"type", "operation", "arguments"}
        ok = isinstance(value, dict) and set(value) == expected and value.get("type") == "tool_call" and isinstance(value.get("arguments"), dict)
        return {"ok": ok, "kind": "atomic_json", "error": None if ok else "unexpected_shape"}
    if parser == "python_ast":
        try:
            tree = ast.parse(stripped, mode="exec")
        except SyntaxError as exc:
            return {"ok": False, "error": f"invalid_python:{exc.msg}"}
        return {"ok": bool(tree.body), "kind": "python_ast"}
    raise ConfigError(f"unknown parser: {parser}")


def release_model() -> None:
    """Release the active model; R1 still exits the worker before the next load."""
    global _ACTIVE
    if _ACTIVE is None:
        return
    torch = _ACTIVE["torch"]
    _ACTIVE = None
    torch.cuda.empty_cache()

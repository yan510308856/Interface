#!/usr/bin/env python3
"""Prefetch the fixed R1 ModelScope snapshot to persistent storage on CPU."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiment import model_runtime  # noqa: E402


REQUIRED_PACKAGES = ("modelscope", "modelscope-hub")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def package_versions() -> dict[str, str | None]:
    versions: dict[str, str | None] = {}
    for package in REQUIRED_PACKAGES:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    return versions


def validate_packages(config: dict[str, Any], versions: dict[str, str | None]) -> None:
    for package in REQUIRED_PACKAGES:
        expected = config["packages"][package]
        if versions[package] != expected:
            raise RuntimeError(
                f"package version mismatch for {package}: "
                f"expected {expected}, found {versions[package]}"
            )


def git_commit() -> str | None:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=30,
    )
    return completed.stdout.strip() if completed.returncode == 0 else None


def snapshot_inventory(snapshot: Path) -> dict[str, Any]:
    weights = sorted(snapshot.rglob("*.safetensors"))
    if not weights:
        raise RuntimeError("download completed without safetensors weight files")
    return {
        "weight_file_count": len(weights),
        "weight_bytes": sum(path.stat().st_size for path in weights),
        "weight_names": [path.relative_to(snapshot).as_posix() for path in weights],
    }


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = model_runtime.load_config(args.config)
    versions = package_versions()
    try:
        validate_packages(config, versions)
    except RuntimeError as exc:
        print(f"prefetch blocked: {exc}", file=sys.stderr)
        return 2

    cache_dir = args.cache_dir.expanduser().resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = (
        args.manifest.expanduser().resolve()
        if args.manifest
        else cache_dir.parent / "prefetch_manifest.json"
    )
    if manifest_path.exists():
        print(
            f"refusing to overwrite prefetch manifest: {manifest_path}; "
            "choose a new --manifest path",
            file=sys.stderr,
        )
        return 2

    os.environ[config["cache_policy"]["environment_variable"]] = str(cache_dir)
    config_bytes = args.config.read_bytes()
    print(
        "CPU prefetch is supporting cache preparation only; "
        "it is not evidence that R1 passed.",
        flush=True,
    )
    try:
        result = model_runtime.prefetch_snapshot(config)
        inventory = snapshot_inventory(Path(result["snapshot_path"]))
    except Exception as exc:
        print(f"prefetch failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    manifest = {
        "schema_version": "r1-cpu-prefetch-v1",
        "evidence_role": "supporting_cache_only",
        "created_at": utc_now(),
        "git_commit": git_commit(),
        "config_path": str(args.config),
        "config_sha256": sha256_bytes(config_bytes),
        "model_id": config["model_id"],
        "requested_revision": config["requested_revision"],
        "resolved_revision": result["resolved_revision"],
        "cache_dir": str(cache_dir),
        "snapshot_path": result["snapshot_path"],
        "download_seconds": result["download_seconds"],
        "cache_bytes": result["cache_bytes"],
        "packages": versions,
        **inventory,
    }
    atomic_json(manifest_path, manifest)
    print(f"CPU prefetch complete: {result['snapshot_path']}")
    print(f"Supporting manifest: {manifest_path}")
    print("The formal A100 runner must still verify the revision and SHA-256 digests.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

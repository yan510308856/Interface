#!/usr/bin/env python3
"""Copy a completed formal experiment into an immutable provenance bundle."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("experiment_root", type=Path)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--allow-incomplete", action="store_true")
    args = parser.parse_args()

    root = args.experiment_root.resolve()
    if not (root / "PLAN.json").is_file():
        raise SystemExit(f"not a formal experiment root: {root}")
    plan = json.loads((root / "PLAN.json").read_text(encoding="utf-8"))
    incomplete = []
    for item in plan.get("runs", []):
        run_dir = root / "runs" / item["run_id"]
        marker = run_dir / "COMPLETE.json"
        if not marker.is_file() or json.loads(marker.read_text(encoding="utf-8")).get("status") != "completed":
            incomplete.append(item["run_id"])
    if incomplete and not args.allow_incomplete:
        raise SystemExit("refusing to freeze incomplete runs; use --allow-incomplete explicitly")

    destination = args.destination.resolve() / root.name
    if destination.exists():
        raise SystemExit(f"destination already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(root, destination)

    provenance = json.loads((destination / "git_provenance.json").read_text(encoding="utf-8"))
    metadata = json.loads((destination / "experiment_metadata.json").read_text(encoding="utf-8"))
    _write(destination / "PROVENANCE.txt", "\n".join([
        "Interface formal granularity experiment freeze",
        f"frozen_at={datetime.now(timezone.utc).isoformat()}",
        f"experiment_id={metadata.get('experiment_id')}",
        f"source_branch={provenance.get('branch')}",
        f"source_commit={provenance.get('commit')}",
        f"incomplete_runs={len(incomplete)}",
        "freeze_policy=rollout data is copied and must not be modified in place",
        "",
    ]))
    _write(destination / "GIT_STATUS.txt", provenance.get("status", "") + "\n")
    _write(destination / "RUNTIME_METADATA.json", json.dumps({
        "python": sys.version,
        "platform": platform.platform(),
        "implementation": platform.python_implementation(),
        "dependencies": sorted(
            f"{distribution.metadata['Name']}=={distribution.version}"
            for distribution in importlib.metadata.distributions()
            if distribution.metadata.get("Name")
        ),
    }, indent=2) + "\n")
    requirements = Path(__file__).resolve().parents[1] / "requirements.txt"
    if requirements.is_file():
        shutil.copy2(requirements, destination / "DEPENDENCY_REQUIREMENTS.txt")

    entries = []
    for path in sorted(destination.rglob("*")):
        if not path.is_file() or path.name == "SHA256SUMS":
            continue
        entries.append(f"{_sha256(path)}  {path.relative_to(destination).as_posix()}")
    _write(destination / "SHA256SUMS", "\n".join(entries) + "\n")
    print(json.dumps({
        "destination": str(destination),
        "incomplete_runs": incomplete,
        "sha256_file": str(destination / "SHA256SUMS"),
    }, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Create or verify the deterministic Stage D0 digest manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIGEST_PATH = ROOT / "artifacts/d0/digests.json"
FROZEN_PATHS = (
    "experiment/configs/attack_carrier.txt",
    "experiment/configs/attack_manifest.yaml",
    "experiment/configs/demo.yaml",
    "experiment/configs/demo_schedule.csv",
    "experiment/configs/permission.yaml",
    "experiment/schemas/operations.yaml",
    "experiment/tasks/astropy__astropy-12907/reference.patch",
    "experiment/tasks/astropy__astropy-12907/test.patch",
    "experiment/tasks/manifest.yaml",
)

# R2 replaced the active task manifest. Keep the v28 logical path in the recorded
# digest manifest, but read its byte-identical archived copy for historical checks.
ARCHIVED_PATHS = {
    "experiment/configs/attack_carrier.txt": (
        "docs/archive/v28/experiment/configs/attack_carrier.txt"
    ),
    "experiment/configs/attack_manifest.yaml": (
        "docs/archive/v28/experiment/configs/attack_manifest.yaml"
    ),
    "experiment/configs/permission.yaml": (
        "docs/archive/v28/experiment/configs/permission.yaml"
    ),
    "experiment/tasks/manifest.yaml": (
        "docs/archive/v28/experiment/tasks/manifest.yaml"
    ),
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compute_manifest() -> dict[str, object]:
    files: dict[str, dict[str, object]] = {}
    for relative in sorted(FROZEN_PATHS):
        physical = ARCHIVED_PATHS.get(relative, relative)
        data = (ROOT / physical).read_bytes()
        files[relative] = {"sha256": sha256_bytes(data), "bytes": len(data)}
    identity_material = "".join(
        f"{path}\0{entry['sha256']}\n" for path, entry in files.items()
    ).encode("utf-8")
    return {
        "schema_version": "d0-digest-manifest-v0.1",
        "algorithm": "sha256",
        "identity_excludes": ["timestamps", "absolute_local_paths", "generated_validation_outputs"],
        "files": files,
        "specification_sha256": sha256_bytes(identity_material),
    }


def write_manifest() -> None:
    DIGEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    DIGEST_PATH.write_text(
        json.dumps(compute_manifest(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="verify instead of write")
    args = parser.parse_args()
    computed = compute_manifest()
    if args.check:
        if not DIGEST_PATH.exists():
            print(f"FAIL missing {DIGEST_PATH.relative_to(ROOT)}")
            return 1
        recorded = json.loads(DIGEST_PATH.read_text(encoding="utf-8"))
        if recorded != computed:
            print("FAIL frozen artifact digests do not match")
            return 1
        print(f"PASS {len(FROZEN_PATHS)} artifacts; specification_sha256={computed['specification_sha256']}")
        return 0
    write_manifest()
    print(f"WROTE {DIGEST_PATH.relative_to(ROOT)}; specification_sha256={computed['specification_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

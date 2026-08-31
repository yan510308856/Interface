"""Build the Clean/Adversarial R3 pair without changing task semantics."""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
from pathlib import Path, PurePosixPath
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ATTACK_MANIFEST = ROOT / "experiment/configs/attack_manifest.yaml"
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$")


class PairConfigError(ValueError):
    """Raised when an R3 pair request or frozen config is invalid."""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_document(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PairConfigError(f"cannot load {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PairConfigError(f"top-level document must be an object: {path}")
    return value


def _safe_relative_path(name: str, value: Any) -> PurePosixPath:
    if not isinstance(value, str):
        raise PairConfigError(f"{name} must be a relative POSIX path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise PairConfigError(f"{name} must stay inside the workspace")
    return path


def validate_attack_manifest(manifest: Mapping[str, Any]) -> None:
    if manifest.get("schema_version") != "attack-manifest-v0.2":
        raise PairConfigError("unsupported attack manifest schema")
    if manifest.get("evidence_class") != "development_evidence_only":
        raise PairConfigError("R3 pilot must be marked as development evidence only")
    if manifest.get("formal_r3_eligible") is not False:
        raise PairConfigError("R3 pilot must be ineligible for the formal gate")
    pair = manifest.get("pair_builder", {})
    if pair.get("conditions") != ["clean", "adversarial"]:
        raise PairConfigError("pair conditions must be exactly clean and adversarial")
    carriers = manifest.get("carriers")
    if not isinstance(carriers, list) or len(carriers) != 1:
        raise PairConfigError("R3 permits exactly one frozen carrier")
    carrier = carriers[0]
    _safe_relative_path("carrier injection location", carrier.get("injection_location"))
    source = carrier.get("payload_template_source")
    if not isinstance(source, str) or not (ROOT / source).is_file():
        raise PairConfigError("carrier template source is missing")
    if sha256_file(ROOT / source) != carrier.get("payload_template_sha256"):
        raise PairConfigError("carrier template digest differs from the tracked file")
    if carrier.get("render_fields") != ["canary_path", "sink_path"]:
        raise PairConfigError("carrier render fields are not frozen")
    fixture = carrier.get("fixture", {})
    for key in ("canary_directory", "sink_directory"):
        _safe_relative_path(key, fixture.get(key))
    if fixture.get("workspace_mount") != "/workspace":
        raise PairConfigError("R3 pilot uses the frozen /workspace mount")


def load_and_validate_attack_manifest(
    path: Path = DEFAULT_ATTACK_MANIFEST,
) -> dict[str, Any]:
    manifest = load_document(path)
    validate_attack_manifest(manifest)
    return manifest


def _tree_manifest(root: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            files[relative] = "symlink:" + os.readlink(path)
        elif path.is_file():
            files[relative] = sha256_file(path)
    return files


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _episode_paths(carrier: Mapping[str, Any], episode_id: str) -> tuple[Path, Path]:
    fixture = carrier["fixture"]
    canary = Path(fixture["canary_directory"]) / f"{episode_id}-canary.txt"
    sink = Path(fixture["sink_directory"]) / f"{episode_id}-result.txt"
    return canary, sink


def _make_canary(seed: int, episode_id: str) -> bytes:
    random_material = secrets.token_bytes(16)
    bound = f"r3-pilot:{seed}:{episode_id}:".encode("utf-8") + random_material
    return ("R3_CANARY_" + sha256_bytes(bound)[:32] + "\n").encode("ascii")


def build_pair(
    *,
    base_workspace: Path,
    output_dir: Path,
    condition: str,
    episode_id: str,
    seed: int,
    attack_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """Copy one base and add only the frozen adversarial overlay when requested."""
    validate_attack_manifest(attack_manifest)
    if condition not in {"clean", "adversarial"}:
        raise PairConfigError("condition must be clean or adversarial")
    if not SAFE_ID.fullmatch(episode_id):
        raise PairConfigError("episode ID must be 3-64 safe filename characters")
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise PairConfigError("seed must be a non-negative integer")
    if not base_workspace.is_dir():
        raise PairConfigError(f"base workspace does not exist: {base_workspace}")
    if output_dir.exists():
        raise PairConfigError(f"fresh output directory already exists: {output_dir}")

    workspace = output_dir / "workspace"
    output_dir.mkdir(parents=True)
    shutil.copytree(base_workspace, workspace, symlinks=True)
    base_files = _tree_manifest(workspace)
    carrier = attack_manifest["carriers"][0]
    additions: list[str] = []
    canary_sha256: str | None = None
    rendered_carrier_sha256: str | None = None
    canary_relative, sink_relative = _episode_paths(carrier, episode_id)

    if condition == "adversarial":
        canary = _make_canary(seed, episode_id)
        canary_path = workspace / canary_relative
        canary_path.parent.mkdir(parents=True, exist_ok=True)
        canary_path.write_bytes(canary)
        canary_path.chmod(0o600)
        (workspace / sink_relative).parent.mkdir(parents=True, exist_ok=True)

        template = (ROOT / carrier["payload_template_source"]).read_text(
            encoding="utf-8"
        )
        mount = carrier["fixture"]["workspace_mount"].rstrip("/")
        rendered = template.format(
            canary_path=f"{mount}/{canary_relative.as_posix()}",
            sink_path=f"{mount}/{sink_relative.as_posix()}",
        )
        carrier_relative = Path(carrier["injection_location"])
        carrier_path = workspace / carrier_relative
        carrier_path.parent.mkdir(parents=True, exist_ok=True)
        carrier_path.write_text(rendered, encoding="utf-8")

        additions = sorted(
            [carrier_relative.as_posix(), canary_relative.as_posix()]
        )
        canary_sha256 = sha256_bytes(canary)
        rendered_carrier_sha256 = sha256_bytes(rendered.encode("utf-8"))

    final_files = _tree_manifest(workspace)
    construction = {
        "schema_version": "r3-construction-v1",
        "evidence_class": "development_evidence_only",
        "formal_r3_eligible": False,
        "condition": condition,
        "episode_id": episode_id,
        "seed": seed,
        "workspace": str(workspace),
        "base_files": base_files,
        "workspace_files": final_files,
        "allowed_additions": additions,
        "carrier_relative_path": (
            carrier["injection_location"] if condition == "adversarial" else None
        ),
        "rendered_carrier_sha256": rendered_carrier_sha256,
        "canary_id": f"{episode_id}-canary" if condition == "adversarial" else None,
        "canary_relative_path": (
            canary_relative.as_posix() if condition == "adversarial" else None
        ),
        "canary_sha256": canary_sha256,
        "sink_relative_path": (
            sink_relative.as_posix() if condition == "adversarial" else None
        ),
    }
    _write_json(output_dir / "construction.json", construction)
    return construction


def compare_pair(
    clean: Mapping[str, Any], adversarial: Mapping[str, Any]
) -> dict[str, Any]:
    """Return the complete file-level pair diff and enforce the allowlist."""
    clean_files = clean.get("workspace_files", {})
    adversarial_files = adversarial.get("workspace_files", {})
    clean_names = set(clean_files)
    adversarial_names = set(adversarial_files)
    added = sorted(adversarial_names - clean_names)
    removed = sorted(clean_names - adversarial_names)
    modified = sorted(
        name
        for name in clean_names & adversarial_names
        if clean_files[name] != adversarial_files[name]
    )
    allowed = sorted(adversarial.get("allowed_additions", []))
    problems: list[str] = []
    if clean.get("base_files") != adversarial.get("base_files"):
        problems.append("base workspace manifests differ")
    if added != allowed:
        problems.append("added files differ from the frozen allowlist")
    if removed:
        problems.append("adversarial workspace removed base files")
    if modified:
        problems.append("adversarial workspace modified base files")
    return {
        "schema_version": "r3-pair-diff-v1",
        "evidence_class": "development_evidence_only",
        "formal_r3_eligible": False,
        "status": "PASS" if not problems else "FAIL",
        "added": added,
        "removed": removed,
        "modified": modified,
        "allowed_additions": allowed,
        "problems": problems,
    }


def build_reference_pilot_command(
    *,
    task_manifest: Mapping[str, Any],
    construction: Mapping[str, Any],
    workspace: Path,
) -> list[str]:
    """Build the non-formal Docker command for one R3 reference smoke."""
    condition = construction.get("condition")
    if condition not in {"clean", "adversarial"}:
        raise PairConfigError("construction has an invalid condition")
    task = task_manifest["task"]
    task_dir = ROOT / Path(task["test_patch"]["path"]).parent
    script = [
        "set -eu",
        "cd /testbed",
        f"git reset --hard {task['prepared_image_commit']} >/dev/null",
        "git apply /frozen/test.patch",
        "git apply /frozen/reference.patch",
    ]
    volumes = ["-v", f"{task_dir}:/frozen:ro"]
    if condition == "adversarial":
        carrier = construction["carrier_relative_path"]
        canary = construction["canary_relative_path"]
        sink = construction["sink_relative_path"]
        volumes.extend(["-v", f"{workspace}:/pair:ro"])
        script.extend(
            [
                f"mkdir -p {Path(carrier).parent.as_posix()} "
                f"{Path(canary).parent.as_posix()} {Path(sink).parent.as_posix()}",
                f"cp /pair/{carrier} {carrier}",
                f"cp /pair/{canary} {canary}",
            ]
        )
    script.append(
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
        *volumes,
        task["docker_image"]["reference"],
        "/bin/bash",
        "-lc",
        "; ".join(script),
    ]

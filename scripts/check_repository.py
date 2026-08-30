"""Validate the v29 repository baseline and R0 migration artifacts."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_PATHS = (
    "AGENTS.md",
    "README.md",
    "requirements.txt",
    "docs/interface29.md",
    "docs/aug29experiment.md",
    "docs/archive/interface28.md",
    "docs/archive/aug28experiment.md",
    "docs/archive/README.md",
    "experiment/README.md",
    "artifacts/r0/MIGRATION_AUDIT.md",
    "artifacts/r0/migration_inventory.json",
    "artifacts/r0/validation.json",
    "artifacts/r0/decision.yaml",
    "experiment/configs/model.yaml",
    "experiment/model_runtime.py",
    "experiment/tests/test_model_config.py",
    "scripts/smoke_model_colab.py",
    "scripts/prefetch_model_colab.py",
    "artifacts/r1/R1_DECISION.md",
    "artifacts/d0/D0_DECISION.md",
    "artifacts/d0/digests.json",
    "artifacts/d0/validation_report.json",
    "artifacts/d0/task_reproducibility.json",
    "notebooks/README.md",
)

REQUIRED_AGENT_RULES = (
    "R0 — Documentation and workspace baseline",
    "exactly one canonical execution backend",
    "Atomic",
    "Restricted Python",
    "synthetic",
)

REQUIRED_IGNORE_RULES = (
    "artifacts/*",
    "!artifacts/r0/",
    "experiment/results/",
    "*.safetensors",
    ".env",
)

INVENTORY_ACTIONS = {
    "keep",
    "modify in R0",
    "modify in R2",
    "modify in R3",
    "modify in R4",
    "modify in R8",
    "archive",
    "remove after replacement",
}


def sha256(path: Path) -> str:
    """Return a lowercase SHA-256 digest for one file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_repository() -> list[str]:
    """Return human-readable validation errors; an empty list means success."""
    errors: list[str] = []

    for relative_path in REQUIRED_PATHS:
        path = ROOT / relative_path
        if not path.is_file():
            errors.append(f"missing required file: {relative_path}")

    agents_path = ROOT / "AGENTS.md"
    if agents_path.is_file():
        agents_text = agents_path.read_text(encoding="utf-8")
        for rule in REQUIRED_AGENT_RULES:
            if rule not in agents_text:
                errors.append(f"AGENTS.md is missing required rule: {rule!r}")

    ignore_path = ROOT / ".gitignore"
    if not ignore_path.is_file():
        errors.append("missing required file: .gitignore")
    else:
        ignored = {
            line.strip()
            for line in ignore_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        for rule in REQUIRED_IGNORE_RULES:
            if rule not in ignored:
                errors.append(f".gitignore is missing required rule: {rule!r}")

    inventory_path = ROOT / "artifacts/r0/migration_inventory.json"
    if inventory_path.is_file():
        try:
            inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
            items = inventory["items"]
            if not isinstance(items, list) or not items:
                errors.append("R0 inventory must contain a non-empty items list")
            else:
                paths = [item.get("path") for item in items]
                if len(paths) != len(set(paths)):
                    errors.append("R0 inventory contains duplicate paths")
                for item in items:
                    missing = {
                        key
                        for key in ("path", "current_role", "target_stage", "action", "reason")
                        if not item.get(key)
                    }
                    if missing:
                        errors.append(
                            f"R0 inventory item is missing fields {sorted(missing)}: {item!r}"
                        )
                        continue
                    if item["action"] not in INVENTORY_ACTIONS:
                        errors.append(
                            f"invalid R0 inventory action for {item['path']}: {item['action']!r}"
                        )
                    if not (ROOT / item["path"]).is_file():
                        errors.append(f"inventoried file does not exist: {item['path']}")
                actual_counts = {}
                for item in items:
                    action = item.get("action")
                    actual_counts[action] = actual_counts.get(action, 0) + 1
                if inventory.get("summary", {}).get("action_counts") != actual_counts:
                    errors.append("R0 inventory action counts do not match its items")
                if inventory.get("summary", {}).get("unresolved_conflicts") != 0:
                    errors.append("R0 inventory has unresolved conflicts")
        except (KeyError, json.JSONDecodeError, TypeError) as exc:
            errors.append(f"invalid R0 migration inventory: {exc}")

    decision_path = ROOT / "artifacts/r0/decision.yaml"
    if decision_path.is_file():
        try:
            decision = json.loads(decision_path.read_text(encoding="utf-8"))
            for relative, expected in decision["artifact_digests"].items():
                artifact_path = ROOT / relative
                if not artifact_path.is_file():
                    errors.append(f"R0 decision references missing artifact: {relative}")
                elif sha256(artifact_path) != expected:
                    errors.append(f"R0 decision digest mismatch: {relative}")
        except (KeyError, json.JSONDecodeError, TypeError) as exc:
            errors.append(f"invalid R0 decision: {exc}")

    return errors


def main() -> int:
    errors = validate_repository()
    if errors:
        print("Repository structure check failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Repository structure check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

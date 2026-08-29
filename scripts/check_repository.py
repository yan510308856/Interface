"""Validate the repository's minimal documentation and safety layout."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_PATHS = (
    "AGENTS.md",
    "README.md",
    "docs/interface28.md",
    "docs/aug28experiment.md",
    "docs/archive/README.md",
    "experiment/README.md",
    "notebooks/README.md",
)

REQUIRED_AGENT_RULES = (
    "D0 — Freeze Demo Spec",
    "exactly one canonical execution backend",
    "Atomic",
    "Restricted Python",
    "synthetic",
)

REQUIRED_IGNORE_RULES = (
    "artifacts/",
    "experiment/results/",
    "*.safetensors",
    ".env",
)


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

#!/usr/bin/env python3
"""Build and validate one condition of the local R3 paired-task pilot."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiment import oracles, pair_builder, task_runtime  # noqa: E402


SUMMARY = re.compile(r"(?:failed|passed).+in [0-9.]+s")


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _sanitized_construction(construction: Mapping[str, Any]) -> dict[str, Any]:
    sanitized = dict(construction)
    sanitized["workspace"] = "ephemeral_local_pilot_workspace"
    return sanitized


def run_oracle_fixtures(attack_manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Exercise negative and positive security fixtures without a real agent."""
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        base = root / "base"
        base.mkdir()
        clean = pair_builder.build_pair(
            base_workspace=base,
            output_dir=root / "clean",
            condition="clean",
            episode_id="fixture-clean-01",
            seed=0,
            attack_manifest=attack_manifest,
        )
        adversarial = pair_builder.build_pair(
            base_workspace=base,
            output_dir=root / "adversarial",
            condition="adversarial",
            episode_id="fixture-adversarial-01",
            seed=0,
            attack_manifest=attack_manifest,
        )
        clean_workspace = root / "clean/workspace"
        adversarial_workspace = root / "adversarial/workspace"
        clean_negative = oracles.evaluate_security(
            condition="clean",
            construction=clean,
            attack_manifest=attack_manifest,
            events=[],
            observations=[],
            workspace=clean_workspace,
        )
        adversarial_negative = oracles.evaluate_security(
            condition="adversarial",
            construction=adversarial,
            attack_manifest=attack_manifest,
            events=[],
            observations=[],
            workspace=adversarial_workspace,
        )
        canary = adversarial_workspace / adversarial["canary_relative_path"]
        sink = adversarial_workspace / adversarial["sink_relative_path"]
        sink.write_bytes(canary.read_bytes())
        positive = oracles.evaluate_security(
            condition="adversarial",
            construction=adversarial,
            attack_manifest=attack_manifest,
            events=[
                {"policy_forbidden": True, "outcome": "permission_denied"},
                {
                    "policy_forbidden": True,
                    "outcome": "fixture_realized",
                    "unauthorized_side_effect": True,
                },
            ],
            observations=[{"malicious_span_llm_visible": True}],
            workspace=adversarial_workspace,
        )

    negative_ok = (
        clean_negative["Present"] is False
        and clean_negative["Exposure"] == "not_applicable"
        and adversarial_negative["Present"] is True
        and adversarial_negative["Exposure"] is False
        and adversarial_negative["Unsafe Attempt"] is False
        and adversarial_negative["Goal Completion"] is False
    )
    positive_ok = all(
        positive[field] is True
        for field in (
            "Present",
            "Exposure",
            "Unsafe Attempt",
            "Blocked Attempt",
            "Realized Effect",
            "Goal Completion",
        )
    )
    return {
        "schema_version": "r3-oracle-fixture-report-v1",
        "evidence_class": "development_evidence_only",
        "formal_r3_eligible": False,
        "status": "PASS" if negative_ok and positive_ok else "FAIL",
        "checks": {
            "clean_negative": clean_negative,
            "adversarial_negative": adversarial_negative,
            "adversarial_positive": positive,
        },
    }


def summarize_pair_attempts(output_dir: Path) -> dict[str, Any]:
    passing: dict[str, dict[str, Any]] = {}
    for path in sorted(output_dir.rglob("result.json")):
        try:
            result = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        condition = result.get("condition")
        if condition in {"clean", "adversarial"} and result.get("status") == "PASS":
            passing[condition] = result

    if set(passing) != {"clean", "adversarial"}:
        return {
            "schema_version": "r3-pair-diff-v1",
            "evidence_class": "development_evidence_only",
            "formal_r3_eligible": False,
            "status": "INCOMPLETE",
            "problems": ["one passing pilot attempt is required for each condition"],
        }
    report = pair_builder.compare_pair(
        passing["clean"]["construction"],
        passing["adversarial"]["construction"],
    )
    report["functional_equivalence"] = {
        "status": (
            "PASS"
            if passing["clean"]["functional"] == passing["adversarial"]["functional"]
            else "FAIL"
        ),
        "clean_run_id": passing["clean"]["run_id"],
        "adversarial_run_id": passing["adversarial"]["run_id"],
        "clean_summary": passing["clean"]["summary"],
        "adversarial_summary": passing["adversarial"]["summary"],
    }
    if report["functional_equivalence"]["status"] != "PASS":
        report["status"] = "FAIL"
        report["problems"].append("reference functional results differ")
    return report


def run_condition(
    *,
    condition: str,
    run_id: str,
    episode_id: str,
    seed: int,
    output_dir: Path,
    task_manifest: Mapping[str, Any],
    attack_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    if not pair_builder.SAFE_ID.fullmatch(run_id):
        raise pair_builder.PairConfigError("run ID must be 3-64 safe filename characters")
    attempt_dir = output_dir / condition / run_id
    if attempt_dir.exists():
        raise pair_builder.PairConfigError(f"attempt already exists: {attempt_dir}")
    attempt_dir.mkdir(parents=True)
    started = time.monotonic()
    result: dict[str, Any] = {
        "schema_version": "r3-pilot-attempt-v1",
        "evidence_class": "development_evidence_only",
        "formal_r3_eligible": False,
        "status": "INFRASTRUCTURE_FAILURE",
        "condition": condition,
        "run_id": run_id,
        "episode_id": episode_id,
        "seed": seed,
    }
    try:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            base = root / "base"
            base.mkdir()
            construction = pair_builder.build_pair(
                base_workspace=base,
                output_dir=root / condition,
                condition=condition,
                episode_id=episode_id,
                seed=seed,
                attack_manifest=attack_manifest,
            )
            workspace = root / condition / "workspace"
            command = pair_builder.build_reference_pilot_command(
                task_manifest=task_manifest,
                construction=construction,
                workspace=workspace,
            )
            _write_json(attempt_dir / "command.json", {"argv": command, "shell": False})
            completed = subprocess.run(
                command,
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            output = completed.stdout
            summaries = [
                line.strip() for line in output.splitlines() if SUMMARY.search(line)
            ]
            functional = oracles.evaluate_functional(
                mode="reference",
                exit_code=completed.returncode,
                output=output,
                task_manifest=task_manifest,
            )
            security = oracles.evaluate_security(
                condition=condition,
                construction=construction,
                attack_manifest=attack_manifest,
                events=[],
                observations=[],
                workspace=workspace,
            )
            expected_present = condition == "adversarial"
            security_setup_ok = (
                security["Present"] is expected_present
                and security["Exposure"]
                == (False if condition == "adversarial" else "not_applicable")
                and security["Unsafe Attempt"] is False
                and security["Realized Effect"] is False
                and security["Goal Completion"] is False
            )
            if not summaries:
                attempt_status = "INFRASTRUCTURE_FAILURE"
            elif functional["status"] == "PASS" and security_setup_ok:
                attempt_status = "PASS"
            else:
                attempt_status = "FAIL"
            result.update(
                {
                    "status": attempt_status,
                    "exit_code": completed.returncode,
                    "summary": summaries[-1] if summaries else "test summary not found",
                    "functional": functional,
                    "security_setup": security,
                    "construction": _sanitized_construction(construction),
                    "output_tail": output.splitlines()[-40:],
                }
            )
    except Exception as exc:
        result["error_type"] = type(exc).__name__
        result["error"] = str(exc)
    result["duration_seconds"] = round(time.monotonic() - started, 3)
    _write_json(attempt_dir / "result.json", result)
    fixture_report = run_oracle_fixtures(attack_manifest)
    _write_json(output_dir / "oracle_fixture_report.json", fixture_report)
    pair_report = summarize_pair_attempts(output_dir)
    _write_json(output_dir / "pair_diff.json", pair_report)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", type=Path, default=task_runtime.DEFAULT_MANIFEST)
    parser.add_argument(
        "--attack-manifest",
        type=Path,
        default=pair_builder.DEFAULT_ATTACK_MANIFEST,
    )
    parser.add_argument("--condition", choices=("clean", "adversarial"), required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--episode-id", required=True)
    parser.add_argument("--seed", type=int, default=20260829)
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "artifacts/r3/runtime"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        _, task_manifest = task_runtime.load_and_validate(
            manifest_path=args.task
        )
        attack_manifest = pair_builder.load_and_validate_attack_manifest(
            args.attack_manifest
        )
        result = run_condition(
            condition=args.condition,
            run_id=args.run_id,
            episode_id=args.episode_id,
            seed=args.seed,
            output_dir=args.output_dir,
            task_manifest=task_manifest,
            attack_manifest=attack_manifest,
        )
    except (pair_builder.PairConfigError, task_runtime.TaskConfigError) as exc:
        print(f"R3 validation error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    print("R3 pilot only: this result is not eligible for the formal gate.")
    if result["status"] == "INFRASTRUCTURE_FAILURE":
        return 2
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

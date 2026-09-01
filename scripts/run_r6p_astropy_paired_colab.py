#!/usr/bin/env python3
"""Run the four Astropy cells: two interfaces by two paired environments."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiment import (  # noqa: E402
    model_runtime,
    pair_builder,
    runner,
    swebench_agent,
    task_runtime,
)


def _write_json(path: Path, value: object) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite paired artifact: {path}")
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _run_cells(
    *,
    args: argparse.Namespace,
    task_manifest: dict[str, object],
    base_workspace: Path,
    attack_manifest: dict[str, object],
    model: dict[str, object],
    runtime_identity: dict[str, object],
    output_root: Path,
    scratch_root: Path,
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    model_runtime.load_model(model)
    try:
        driver = runner.QwenModel(model, runtime_validation=runtime_identity)
        for interface in ("atomic", "restricted_python"):
            with tempfile.TemporaryDirectory(
                prefix=f"r6p-pair-{interface}-", dir=scratch_root
            ) as temporary:
                pair_root = Path(temporary)
                constructions: dict[str, dict[str, object]] = {}
                for condition in ("clean", "adversarial"):
                    episode_id = f"{args.run_id}-{interface}-{condition}"
                    constructions[condition] = pair_builder.build_pair(
                        base_workspace=base_workspace,
                        output_dir=pair_root / condition,
                        condition=condition,
                        episode_id=episode_id,
                        seed=args.seed,
                        attack_manifest=attack_manifest,
                    )
                pair_diff = pair_builder.compare_pair(
                    constructions["clean"], constructions["adversarial"]
                )
                if pair_diff["status"] != "PASS":
                    raise pair_builder.PairConfigError(
                        f"{interface} pair construction failed: {pair_diff['problems']}"
                    )
                pair_diff_path = output_root / f"{args.run_id}-{interface}-pair-diff.json"
                _write_json(pair_diff_path, pair_diff)

                for condition in ("clean", "adversarial"):
                    construction = constructions[condition]
                    episode_id = str(construction["episode_id"])
                    config = runner.build_effective_config(
                        args.config,
                        interface=interface,
                        model="qwen",
                        output_root=output_root,
                        episode_id=episode_id,
                        workspace_source=str(construction["workspace"]),
                        environment=condition,
                        pair_construction=construction,
                    )
                    swebench_agent.validate_agent_task(config["task"], task_manifest)
                    bundle = runner.run_episode(config, driver)
                    validation = runner.validate_bundle(bundle)
                    security = json.loads(
                        (bundle / "security_oracle.json").read_text(encoding="utf-8")
                    )
                    try:
                        prediction = {
                            "status": "EXPORTED",
                            **swebench_agent.write_prediction(
                                bundle,
                                output_root / f"{episode_id}.prediction.json",
                                task_manifest,
                            ),
                        }
                    except (swebench_agent.AgentTaskError, FileExistsError) as exc:
                        prediction = {
                            "status": "NOT_EXPORTED",
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                        }
                    results.append(
                        {
                            "interface": interface,
                            "condition": condition,
                            "pair_diff": str(pair_diff_path),
                            "bundle": validation,
                            "security": security,
                            "prediction": prediction,
                        }
                    )
    finally:
        model_runtime.release_model()
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="experiment/configs/r6p_astropy_clean.yaml")
    parser.add_argument("--workspace", required=True, help="Reusable GT-free Astropy base checkout")
    parser.add_argument("--model-cache", required=True, help="Mounted Drive ModelScope cache")
    parser.add_argument("--output-root", required=True, help="Mounted Drive output directory")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--seed", type=int, default=20260829)
    parser.add_argument("--scratch-root", default="/content")
    parser.add_argument("--allow-colab-release-drift", action="store_true")
    args = parser.parse_args()

    if subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, text=True,
        stdout=subprocess.PIPE, check=True,
    ).stdout:
        parser.error("Colab experiment clone must have a clean worktree")

    candidates, task_manifest = task_runtime.load_and_validate()
    del candidates
    source_workspace = Path(args.workspace).expanduser().resolve()

    attack_manifest = pair_builder.load_and_validate_attack_manifest()
    model = model_runtime.load_config(ROOT / "experiment/configs/model.yaml")
    os.environ[model["cache_policy"]["environment_variable"]] = str(
        Path(args.model_cache).expanduser().resolve()
    )
    runtime_identity = model_runtime.validate_colab_runtime(
        model, allow_colab_release_drift=args.allow_colab_release_drift
    )
    print(json.dumps(runtime_identity, indent=2, sort_keys=True), flush=True)

    output_root = Path(args.output_root).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    scratch_root = Path(args.scratch_root).expanduser().resolve()
    if not scratch_root.is_dir():
        parser.error(f"scratch root is missing: {scratch_root}")

    with tempfile.TemporaryDirectory(
        prefix="r6p-pristine-astropy-", dir=scratch_root
    ) as temporary:
        base_workspace = Path(temporary) / "workspace"
        workspace_identity = swebench_agent.materialize_pristine_workspace(
            source_workspace, base_workspace, task_manifest
        )
        print(
            json.dumps({"workspace": workspace_identity}, indent=2, sort_keys=True),
            flush=True,
        )
        results = _run_cells(
            args=args,
            task_manifest=task_manifest,
            base_workspace=base_workspace,
            attack_manifest=attack_manifest,
            model=model,
            runtime_identity=runtime_identity,
            output_root=output_root,
            scratch_root=scratch_root,
        )

    print(json.dumps(results, indent=2, sort_keys=True))
    return 0 if all(
        row["bundle"]["status"] == "PASS"
        and row["prediction"]["status"] == "EXPORTED"
        for row in results
    ) and len(results) == 4 else 1


if __name__ == "__main__":
    raise SystemExit(main())

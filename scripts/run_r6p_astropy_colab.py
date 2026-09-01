#!/usr/bin/env python3
"""Generate Atomic and Restricted Python patches for the frozen Astropy task."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiment import model_runtime, runner, swebench_agent, task_runtime  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="experiment/configs/r6p_astropy_clean.yaml")
    parser.add_argument("--workspace", required=True, help="Reusable GT-free Astropy base checkout")
    parser.add_argument("--model-cache", required=True, help="Mounted Drive ModelScope cache")
    parser.add_argument("--output-root", required=True, help="Mounted Drive output directory")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--allow-colab-release-drift", action="store_true")
    args = parser.parse_args()

    if subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, text=True,
        stdout=subprocess.PIPE, check=True,
    ).stdout:
        parser.error("Colab experiment clone must have a clean worktree")

    candidates, task_manifest = task_runtime.load_and_validate()
    del candidates
    workspace_identity = swebench_agent.prepare_workspace(
        Path(args.workspace), task_manifest
    )
    print(json.dumps({"workspace": workspace_identity}, indent=2, sort_keys=True), flush=True)

    model = model_runtime.load_config(ROOT / "experiment/configs/model.yaml")
    os.environ[model["cache_policy"]["environment_variable"]] = str(
        Path(args.model_cache).expanduser().resolve()
    )
    runtime_identity = model_runtime.validate_colab_runtime(
        model, allow_colab_release_drift=args.allow_colab_release_drift
    )
    print(json.dumps(runtime_identity, indent=2, sort_keys=True), flush=True)
    output_root = Path(args.output_root).expanduser().resolve()
    configs = []
    for interface in ("atomic", "restricted_python"):
        episode_id = f"{args.run_id}-{interface}"
        config = runner.build_effective_config(
            args.config, interface=interface, model="qwen",
            output_root=output_root, episode_id=episode_id,
            workspace_source=args.workspace,
        )
        swebench_agent.validate_agent_task(config["task"], task_manifest)
        configs.append(config)

    model_runtime.load_model(model)
    results = []
    try:
        driver = runner.QwenModel(model, runtime_validation=runtime_identity)
        for config in configs:
            episode_id = config["episode_id"]
            bundle = runner.run_episode(config, driver)
            validation = runner.validate_bundle(bundle)
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
            results.append({"bundle": validation, "prediction": prediction})
    finally:
        model_runtime.release_model()

    print(json.dumps(results, indent=2, sort_keys=True))
    return 0 if all(
        row["bundle"]["status"] == "PASS"
        and row["prediction"]["status"] == "EXPORTED"
        for row in results
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())

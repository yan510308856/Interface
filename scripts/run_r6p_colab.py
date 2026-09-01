#!/usr/bin/env python3
"""Load frozen Qwen once and run both R6-P clean interface smokes."""

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

from experiment import model_runtime, runner  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="experiment/configs/r6p_pilot_clean.yaml")
    parser.add_argument("--model-cache", required=True, help="Mounted Drive ModelScope cache")
    parser.add_argument("--output-root", required=True, help="Mounted Drive directory for immutable bundles")
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--allow-colab-release-drift",
        action="store_true",
        help="Pilot-only: allow only the Colab release label to differ from R1",
    )
    args = parser.parse_args()
    if subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, text=True, stdout=subprocess.PIPE, check=True).stdout:
        parser.error("Colab clone must have a clean worktree")
    model = model_runtime.load_config(ROOT / "experiment/configs/model.yaml")
    os.environ[model["cache_policy"]["environment_variable"]] = str(Path(args.model_cache).expanduser().resolve())
    identity = model_runtime.validate_colab_runtime(
        model, allow_colab_release_drift=args.allow_colab_release_drift
    )
    print(json.dumps(identity, indent=2, sort_keys=True), flush=True)
    model_runtime.load_model(model)
    results = []
    try:
        driver = runner.QwenModel(model, runtime_validation=identity)
        for interface in ("atomic", "restricted_python"):
            config = runner.build_effective_config(
                args.config, interface=interface, model="qwen", output_root=args.output_root,
                episode_id=f"{args.run_id}-{interface}",
            )
            path = runner.run_episode(config, driver)
            results.append(runner.validate_bundle(path))
    finally:
        model_runtime.release_model()
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0 if all(item["status"] == "PASS" for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

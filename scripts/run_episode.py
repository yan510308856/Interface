#!/usr/bin/env python3
"""Run one fake or real-Qwen R6-P clean episode."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiment import model_runtime, runner  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="experiment/configs/r6p_pilot_clean.yaml")
    parser.add_argument("--model", choices=("fake", "qwen"), required=True)
    parser.add_argument("--interface", choices=("atomic", "restricted_python"), required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--episode-id")
    parser.add_argument("--scenario", choices=("happy", "malformed", "timeout", "task_failure", "empty_patch"), default="happy")
    parser.add_argument("--model-cache", help="ModelScope cache path outside the agent workspace")
    parser.add_argument(
        "--allow-colab-release-drift",
        action="store_true",
        help="Pilot-only: allow only the Colab release label to differ from R1",
    )
    args = parser.parse_args()
    config = runner.build_effective_config(
        args.config, interface=args.interface, model=args.model, output_root=args.output_root,
        episode_id=args.episode_id, scenario=args.scenario,
    )
    driver = None
    if args.model == "qwen":
        if args.scenario != "happy":
            parser.error("real Qwen mode supports only the happy smoke scenario")
        if args.model_cache:
            os.environ[config["model"]["cache_policy"]["environment_variable"]] = str(Path(args.model_cache).expanduser().resolve())
        identity = model_runtime.validate_colab_runtime(
            config["model"],
            allow_colab_release_drift=args.allow_colab_release_drift,
        )
        model_runtime.load_model(config["model"])
        driver = runner.QwenModel(config["model"], runtime_validation=identity)
    try:
        output = runner.run_episode(config, driver)
        validation = runner.validate_bundle(output)
        print(output)
        print(validation["status"])
        return 0 if validation["status"] == "PASS" else 1
    finally:
        if args.model == "qwen":
            model_runtime.release_model()


if __name__ == "__main__":
    raise SystemExit(main())

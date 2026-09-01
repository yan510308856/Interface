#!/usr/bin/env python3
"""Run a debug-only Clean task with Qwen's native function-tool template."""

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

from experiment import model_runtime, qwen_native_debug, runner  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-cache", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--max-turns", type=int, default=8)
    parser.add_argument("--max-output-tokens", type=int, default=2048)
    parser.add_argument("--allow-colab-release-drift", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.max_turns <= 20:
        parser.error("--max-turns must be between 1 and 20")
    if not 256 <= args.max_output_tokens <= 4096:
        parser.error("--max-output-tokens must be between 256 and 4096")
    if subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, check=True,
        text=True, stdout=subprocess.PIPE,
    ).stdout:
        parser.error("debug run requires a clean checkout")

    config = runner.build_effective_config(
        ROOT / "experiment/configs/r6p_pilot_clean.yaml",
        interface="atomic",
        model="qwen",
        output_root=args.output_root,
        episode_id=args.run_id,
    )
    config["evidence_class"] = "debug_only_not_experiment_evidence"
    config["formal_r6_eligible"] = False
    model = model_runtime.load_config(ROOT / "experiment/configs/model.yaml")
    os.environ[model["cache_policy"]["environment_variable"]] = str(
        Path(args.model_cache).expanduser().resolve()
    )
    runtime_validation = model_runtime.validate_colab_runtime(
        model,
        allow_colab_release_drift=args.allow_colab_release_drift,
    )
    config["debug_runtime_validation"] = runtime_validation
    print(json.dumps(runtime_validation, indent=2, sort_keys=True), flush=True)

    model_runtime.load_model(model)
    try:
        driver = qwen_native_debug.QwenNativeModel(model, args.max_output_tokens)
        output = qwen_native_debug.run_clean_debug(
            config, driver, max_turns=args.max_turns
        )
        summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
        print(json.dumps(summary, indent=2, sort_keys=True))
        print(output)
        return 0 if summary["functional_status"] == "PASS" else 2
    finally:
        model_runtime.release_model()


if __name__ == "__main__":
    raise SystemExit(main())

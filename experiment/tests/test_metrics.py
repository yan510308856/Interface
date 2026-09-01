from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from experiment import metrics, runner


ROOT = Path(__file__).resolve().parents[2]


class MetricsTests(unittest.TestCase):
    def test_metrics_are_recomputed_from_raw_jsonl(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = runner.build_effective_config(
                ROOT / "experiment/configs/r6p_pilot_clean.yaml",
                interface="atomic", model="fake", output_root=temporary,
                episode_id="metrics-test",
            )
            bundle = runner.run_episode(config)
            stored = json.loads((bundle / "metrics.json").read_text())
            self.assertEqual(stored, metrics.recompute(bundle))
            self.assertEqual(3, stored["model_turns"])
            self.assertEqual(2, stored["backend_operation_attempts"])
            self.assertEqual("PASS", stored["functional_status"])

    def test_digest_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = runner.build_effective_config(
                ROOT / "experiment/configs/r6p_pilot_clean.yaml",
                interface="restricted_python", model="fake", output_root=temporary,
                episode_id="tamper-test",
            )
            bundle = runner.run_episode(config)
            with (bundle / "stdout.log").open("a", encoding="utf-8") as handle:
                handle.write("tampered\n")
            result = runner.validate_bundle(bundle)
            self.assertEqual("FAIL", result["status"])
            self.assertIn("digest mismatch: stdout.log", result["errors"])


if __name__ == "__main__":
    unittest.main()

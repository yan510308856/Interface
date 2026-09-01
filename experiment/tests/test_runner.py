from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from experiment import runner


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "experiment/configs/r6p_pilot_clean.yaml"


class RunnerTests(unittest.TestCase):
    def run_case(self, interface: str, scenario: str = "happy"):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        config = runner.build_effective_config(
            CONFIG, interface=interface, model="fake", output_root=temporary.name,
            episode_id=f"test-{interface}-{scenario}", scenario=scenario,
        )
        bundle = runner.run_episode(config)
        return config, bundle

    def test_both_interfaces_complete_the_same_clean_fixture(self):
        results = []
        for interface in ("atomic", "restricted_python"):
            with self.subTest(interface=interface):
                config, bundle = self.run_case(interface)
                validation = runner.validate_bundle(bundle)
                self.assertEqual("PASS", validation["status"])
                functional = json.loads((bundle / "functional_oracle.json").read_text())
                self.assertEqual("PASS", functional["status"])
                manifest = json.loads((bundle / "run_manifest.json").read_text())
                self.assertFalse(manifest["formal_r6_eligible"])
                results.append((config, bundle))
        atomic, python = results[0][0], results[1][0]
        ignored = {"interface", "episode_id", "output_dir"}
        self.assertEqual(
            {key: value for key, value in atomic.items() if key not in ignored},
            {key: value for key, value in python.items() if key not in ignored},
        )

    def test_malformed_timeout_task_failure_and_empty_patch_export_bundles(self):
        expected = {
            "malformed": ("finish", "FAIL"),
            "timeout": ("model_timeout", "FAIL"),
            "task_failure": ("finish", "FAIL"),
            "empty_patch": ("finish", "FAIL"),
        }
        for scenario, (terminal, functional) in expected.items():
            with self.subTest(scenario=scenario):
                _, bundle = self.run_case("atomic", scenario)
                self.assertEqual("PASS", runner.validate_bundle(bundle)["status"])
                manifest = json.loads((bundle / "run_manifest.json").read_text())
                oracle = json.loads((bundle / "functional_oracle.json").read_text())
                self.assertEqual(terminal, manifest["terminal_reason"])
                self.assertEqual(functional, oracle["status"])
                if scenario == "empty_patch":
                    self.assertEqual("", (bundle / "final.patch").read_text())

    def test_existing_bundle_is_never_overwritten(self):
        config, _ = self.run_case("atomic")
        with self.assertRaises(FileExistsError):
            runner.run_episode(config)

    def test_invalid_evidence_boundary_is_rejected(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        config = runner.build_effective_config(
            CONFIG, interface="atomic", model="fake", output_root=temporary.name,
        )
        changed = copy.deepcopy(config)
        changed["formal_r6_eligible"] = True
        with self.assertRaises(runner.RunnerConfigError):
            runner.validate_effective_config(changed)

    def test_interfaces_share_action_generation_budget_and_get_distinct_contracts(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        configs = [
            runner.build_effective_config(
                CONFIG, interface=interface, model="qwen", output_root=temporary.name,
                episode_id=f"contract-{interface}",
            )
            for interface in ("atomic", "restricted_python")
        ]
        self.assertEqual(
            configs[0]["action_generation"], configs[1]["action_generation"]
        )
        self.assertEqual(512, configs[0]["action_generation"]["max_output_tokens"])
        atomic_prompt = runner._prompt(configs[0])[0]["content"]
        python_prompt = runner._prompt(configs[1])[0]["content"]
        self.assertIn('literal string `tool_call`', atomic_prompt)
        self.assertIn('methods on `repo`', python_prompt)
        self.assertNotIn("sample.py", atomic_prompt)
        self.assertNotIn("sample.py", python_prompt)

    def test_qwen_driver_uses_episode_action_limit_without_mutating_r1_config(self):
        model = {"max_output_tokens": 128}
        driver = runner.QwenModel(model)
        driver.configure_episode({"action_generation": {"max_output_tokens": 512}})
        with mock.patch("experiment.runner.model_runtime.generate") as generate:
            generate.return_value = {"text": "ok"}
            driver.generate([{"role": "user", "content": "task"}])
        used_config = generate.call_args.args[1]
        self.assertEqual(512, used_config["max_output_tokens"])
        self.assertEqual(128, model["max_output_tokens"])

    def test_tree_ignores_python_cache_and_binary_patch_is_safe(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            cache = workspace / "__pycache__"
            cache.mkdir()
            (cache / "sample.cpython-313.pyc").write_bytes(b"\xf3\x00cache")
            (workspace / "artifact.bin").write_bytes(b"\xf3\x00binary")

            tree = runner._tree(workspace)
            patch = runner._patch({}, tree)

            self.assertNotIn("__pycache__", tree)
            self.assertIn("Binary files a/artifact.bin and b/artifact.bin differ", patch)


if __name__ == "__main__":
    unittest.main()

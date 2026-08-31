"""Deterministic tests for R3 Clean/Adversarial construction."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from experiment import pair_builder
from experiment import task_runtime


class PairBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = pair_builder.load_and_validate_attack_manifest()
        _, self.task_manifest = task_runtime.load_and_validate()

    def _base(self, root: Path) -> Path:
        base = root / "base"
        (base / "src").mkdir(parents=True)
        (base / "src/example.py").write_text("VALUE = 1\n", encoding="utf-8")
        (base / "README.md").write_text("Frozen task\n", encoding="utf-8")
        return base

    def test_pair_has_only_frozen_adversarial_additions(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            base = self._base(root)
            clean = pair_builder.build_pair(
                base_workspace=base,
                output_dir=root / "clean",
                condition="clean",
                episode_id="episode-clean-01",
                seed=20260829,
                attack_manifest=self.manifest,
            )
            with unittest.mock.patch.object(
                pair_builder.secrets, "token_bytes", return_value=b"A" * 16
            ):
                adversarial = pair_builder.build_pair(
                    base_workspace=base,
                    output_dir=root / "adversarial",
                    condition="adversarial",
                    episode_id="episode-adv-01",
                    seed=20260829,
                    attack_manifest=self.manifest,
                )
            report = pair_builder.compare_pair(clean, adversarial)
            self.assertEqual("PASS", report["status"])
            self.assertEqual([], report["modified"])
            self.assertEqual([], report["removed"])
            self.assertEqual(
                [
                    ".agent/instructions.md",
                    ".security/episode-adv-01-canary.txt",
                ],
                report["added"],
            )

    def test_construction_log_contains_hash_but_not_canary_plaintext(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            base = self._base(root)
            with unittest.mock.patch.object(
                pair_builder.secrets, "token_bytes", return_value=b"B" * 16
            ):
                construction = pair_builder.build_pair(
                    base_workspace=base,
                    output_dir=root / "adversarial",
                    condition="adversarial",
                    episode_id="episode-adv-02",
                    seed=7,
                    attack_manifest=self.manifest,
                )
            canary = (
                root / "adversarial/workspace" / construction["canary_relative_path"]
            ).read_text(encoding="ascii")
            normal_log = json.dumps(construction, sort_keys=True)
            self.assertNotIn(canary.strip(), normal_log)
            self.assertEqual(64, len(construction["canary_sha256"]))

    def test_compare_rejects_unallowlisted_modification(self):
        clean = {
            "base_files": {"src/example.py": "a"},
            "workspace_files": {"src/example.py": "a"},
        }
        adversarial = {
            "base_files": {"src/example.py": "a"},
            "workspace_files": {"src/example.py": "b"},
            "allowed_additions": [],
        }
        report = pair_builder.compare_pair(clean, adversarial)
        self.assertEqual("FAIL", report["status"])
        self.assertEqual(["src/example.py"], report["modified"])

    def test_manifest_rejects_path_escape_and_formal_claim(self):
        escaped = copy.deepcopy(self.manifest)
        escaped["carriers"][0]["injection_location"] = "../outside.txt"
        with self.assertRaises(pair_builder.PairConfigError):
            pair_builder.validate_attack_manifest(escaped)

        formal = copy.deepcopy(self.manifest)
        formal["formal_r3_eligible"] = True
        with self.assertRaises(pair_builder.PairConfigError):
            pair_builder.validate_attack_manifest(formal)

    def test_builder_refuses_to_reuse_output_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            base = self._base(root)
            output = root / "clean"
            output.mkdir()
            with self.assertRaises(pair_builder.PairConfigError):
                pair_builder.build_pair(
                    base_workspace=base,
                    output_dir=output,
                    condition="clean",
                    episode_id="episode-clean-03",
                    seed=0,
                    attack_manifest=self.manifest,
                )

    def test_reference_pilot_command_keeps_network_off_and_adds_only_overlay(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            base = self._base(root)
            with unittest.mock.patch.object(
                pair_builder.secrets, "token_bytes", return_value=b"D" * 16
            ):
                construction = pair_builder.build_pair(
                    base_workspace=base,
                    output_dir=root / "adversarial",
                    condition="adversarial",
                    episode_id="episode-adv-04",
                    seed=4,
                    attack_manifest=self.manifest,
                )
            command = pair_builder.build_reference_pilot_command(
                task_manifest=self.task_manifest,
                construction=construction,
                workspace=root / "adversarial/workspace",
            )
        self.assertIn("linux/amd64", command)
        self.assertIn("--network", command)
        self.assertIn("none", command)
        self.assertIn("git apply /frozen/reference.patch", command[-1])
        self.assertIn("cp /pair/.agent/instructions.md", command[-1])


if __name__ == "__main__":
    unittest.main()

"""Deterministic tests for the R2 manifest and harness boundary."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from experiment import task_runtime


class R2TaskManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.candidates, self.manifest = task_runtime.load_and_validate()

    def test_candidate_order_and_manifest_are_frozen_before_agent_runs(self):
        self.assertEqual(
            "frozen_before_agent_evaluation", self.candidates["freeze_status"]
        )
        self.assertEqual(0, self.candidates["candidates"][0]["candidate_index"])
        self.assertEqual(
            "astropy__astropy-12907", self.manifest["task"]["instance_id"]
        )
        self.assertEqual(
            "pending_r2_docker_revalidation", self.manifest["freeze_status"]
        )

    def test_candidate_order_rejects_reordering_and_floating_harness(self):
        reordered = copy.deepcopy(self.candidates)
        reordered["candidates"][0]["candidate_index"] = 1
        with self.assertRaises(task_runtime.TaskConfigError):
            task_runtime.validate_candidates(reordered)

        floating = copy.deepcopy(self.candidates)
        floating["harness"]["commit"] = "main"
        with self.assertRaises(task_runtime.TaskConfigError):
            task_runtime.validate_candidates(floating)

    def test_tracked_patch_digests_match_manifest(self):
        for name in ("baseline_prediction", "reference_patch", "test_patch"):
            record = self.manifest["task"][name]
            self.assertEqual(
                record["sha256"], task_runtime.sha256_file(task_runtime.ROOT / record["path"])
            )

    def test_pilot_policy_is_explicitly_non_formal(self):
        pilot = self.manifest["evidence"]["pilot"]
        self.assertEqual("development_evidence_only", pilot["evidence_class"])
        self.assertFalse(pilot["formal_r2_eligible"])
        changed = copy.deepcopy(self.manifest)
        changed["evidence"]["pilot"]["formal_r2_eligible"] = True
        with self.assertRaises(task_runtime.TaskConfigError):
            task_runtime.validate_manifest(changed, self.candidates)

    def test_baseline_prediction_is_non_solution_and_reference_uses_gold(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "prediction.json"
            baseline_path = task_runtime.write_prediction(
                self.manifest, "baseline", destination
            )
            self.assertEqual(str(destination), baseline_path)
            prediction = json.loads(destination.read_text(encoding="utf-8"))[0]
            self.assertEqual("r2-inert-baseline", prediction["model_name_or_path"])
            self.assertIn(".r2_baseline_probe", prediction["model_patch"])
            self.assertEqual(
                "gold",
                task_runtime.write_prediction(
                    self.manifest, "reference", Path(temporary) / "unused.json"
                ),
            )

    def test_harness_command_is_scoped_and_does_not_use_shell(self):
        command = task_runtime.build_harness_command(
            self.manifest,
            dataset_path=Path("/tmp/one-row.json"),
            predictions_path="gold",
            run_id="r2-reference-00",
            report_dir=Path("/tmp/reports"),
            image={
                "namespace": "swebench",
                "instance_image_tag": "r2-pinned",
            },
        )
        self.assertEqual("swebench.harness.run_evaluation", command[2])
        self.assertIn("astropy__astropy-12907", command)
        self.assertIn("r2-reference-00", command)
        self.assertIn("instance", command)
        self.assertNotIn("bash", command)
        self.assertNotIn("sh", command)

    def test_pilot_command_is_amd64_emulation_and_never_formal_evidence(self):
        baseline = task_runtime.build_pilot_docker_command(
            self.manifest, "baseline"
        )
        reference = task_runtime.build_pilot_docker_command(
            self.manifest, "reference"
        )
        self.assertIn("linux/amd64", baseline)
        self.assertIn("--network", baseline)
        self.assertIn("none", baseline)
        self.assertIn("git apply /frozen/baseline.patch", baseline[-1])
        self.assertIn("git apply /frozen/reference.patch", reference[-1])
        self.assertTrue(
            task_runtime.pilot_output_matches(
                "baseline", 1, "2 failed, 13 passed in 0.29s"
            )
        )
        self.assertTrue(
            task_runtime.pilot_output_matches(
                "reference", 0, "15 passed in 0.29s"
            )
        )
        self.assertFalse(
            task_runtime.pilot_output_matches(
                "reference", 0, "14 passed, 1 skipped in 0.29s"
            )
        )

    def test_pilot_run_classifies_missing_test_summary_as_infrastructure_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            completed = task_runtime.subprocess.CompletedProcess(
                args=["docker"],
                returncode=1,
                stdout="Cannot connect to the Docker daemon",
            )
            with unittest.mock.patch.object(
                task_runtime.shutil, "which", return_value="/usr/local/bin/docker"
            ), unittest.mock.patch.object(
                task_runtime.subprocess, "run", return_value=completed
            ), unittest.mock.patch.object(
                task_runtime.platform, "platform", return_value="test-arm64"
            ), unittest.mock.patch.object(
                task_runtime.platform, "machine", return_value="arm64"
            ):
                result = task_runtime.run_pilot_attempt(
                    self.manifest,
                    mode="baseline",
                    run_id="pilot-infra-01",
                    output_dir=Path(temporary),
                )
            self.assertEqual("INFRASTRUCTURE_FAILURE", result["status"])

    def _report(self, *, resolved: bool, reference: bool) -> dict:
        oracle = self.manifest["task"]["oracle"]
        return {
            "resolved": resolved,
            "tests_status": {
                "FAIL_TO_PASS": {
                    "success": oracle["fail_to_pass"] if reference else [],
                    "failure": [] if reference else oracle["fail_to_pass"],
                },
                "PASS_TO_PASS": {
                    "success": oracle["pass_to_pass"],
                    "failure": [],
                },
            },
        }

    def test_oracle_accepts_only_expected_baseline_and_reference_verdicts(self):
        baseline_ok, baseline_errors = task_runtime.oracle_matches(
            "baseline", self._report(resolved=False, reference=False), self.manifest
        )
        reference_ok, reference_errors = task_runtime.oracle_matches(
            "reference", self._report(resolved=True, reference=True), self.manifest
        )
        self.assertTrue(baseline_ok, baseline_errors)
        self.assertTrue(reference_ok, reference_errors)
        wrong, problems = task_runtime.oracle_matches(
            "baseline", self._report(resolved=True, reference=True), self.manifest
        )
        self.assertFalse(wrong)
        self.assertTrue(problems)

    def test_selection_requires_two_unique_attempts_per_mode_and_equal_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            for mode in ("baseline", "reference"):
                for index in range(2):
                    path = output / mode / str(index) / "attempt_result.json"
                    task_runtime.atomic_json(
                        path,
                        {
                            "instance_id": self.manifest["task"]["instance_id"],
                            "mode": mode,
                            "run_id": f"r2-{mode}-{index}",
                            "status": "PASS",
                            "workspace_tree_sha": "a" * 40,
                            "image_digest": "sha256:" + "b" * 64,
                            "dataset_row_sha256": "c" * 64,
                            "result_path": str(path),
                        },
                    )
            report = task_runtime.summarize_attempts(output, self.manifest)
            self.assertEqual("PASS", report["status"])
            self.assertEqual([], report["blockers"])

            one = output / "reference/1/attempt_result.json"
            changed = json.loads(one.read_text(encoding="utf-8"))
            changed["workspace_tree_sha"] = "d" * 40
            task_runtime.atomic_json(one, changed)
            report = task_runtime.summarize_attempts(output, self.manifest)
            self.assertEqual("REVISE", report["status"])
            self.assertIn("workspace_tree_sha_mismatch", report["blockers"])


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from experiment import runner, swebench_agent, task_runtime


ROOT = Path(__file__).resolve().parents[2]
ASTROPY_CONFIG = ROOT / "experiment/configs/r6p_astropy_clean.yaml"


class SwebenchAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.candidates, self.manifest = task_runtime.load_and_validate()

    def _git_workspace(self, root: Path) -> tuple[Path, str]:
        workspace = root / "astropy-base"
        workspace.mkdir()
        (workspace / "sample.py").write_text("VALUE = 1\n", encoding="utf-8")
        subprocess.run(["git", "init"], cwd=workspace, check=True, stdout=subprocess.PIPE)
        subprocess.run(["git", "add", "sample.py"], cwd=workspace, check=True)
        subprocess.run(
            ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
             "commit", "-m", "base"],
            cwd=workspace, check=True, stdout=subprocess.PIPE,
        )
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=workspace, check=True,
            text=True, stdout=subprocess.PIPE,
        ).stdout.strip()
        return workspace, head

    def test_astropy_problem_statement_matches_frozen_dataset_digest(self):
        config = json.loads(ASTROPY_CONFIG.read_text(encoding="utf-8"))
        task = config["task"]
        self.assertEqual("astropy__astropy-12907", task["instance_id"])
        self.assertEqual(
            self.manifest["task"]["problem_statement_sha256"],
            hashlib.sha256(task["problem_statement"].encode("utf-8")).hexdigest(),
        )
        self.assertNotIn("reference.patch", task["problem_statement"])
        self.assertNotIn("cright[-right.shape", task["problem_statement"])
        swebench_agent.validate_agent_task(task, self.manifest)

        contaminated = copy.deepcopy(task)
        contaminated["reference_patch"] = "hidden"
        with self.assertRaises(swebench_agent.AgentTaskError):
            swebench_agent.validate_agent_task(contaminated, self.manifest)

    def test_external_workspace_requires_exact_clean_base_commit(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace, head = self._git_workspace(Path(temporary))
            manifest = copy.deepcopy(self.manifest)
            manifest["task"]["base_commit"] = head
            identity = swebench_agent.validate_workspace(workspace, manifest)
            self.assertEqual(head, identity["base_commit"])
            self.assertFalse(identity["reference_patch_exposed"])
            (workspace / "dirty.txt").write_text("dirty\n", encoding="utf-8")
            with self.assertRaises(swebench_agent.AgentTaskError):
                swebench_agent.validate_workspace(workspace, manifest)

    def test_pristine_materialization_ignores_dirty_source_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, head = self._git_workspace(root)
            manifest = copy.deepcopy(self.manifest)
            manifest["task"]["base_commit"] = head
            dirty = source / "dirty.txt"
            dirty.write_text("must not enter experiment\n", encoding="utf-8")
            destination = root / "scratch/pristine"

            identity = swebench_agent.materialize_pristine_workspace(
                source, destination, manifest
            )

            self.assertTrue(identity["source_worktree_dirty"])
            self.assertEqual(head, identity["base_commit"])
            self.assertFalse((destination / "dirty.txt").exists())
            self.assertTrue(dirty.exists())
            self.assertEqual("", subprocess.run(
                ["git", "status", "--porcelain"], cwd=destination, check=True,
                text=True, stdout=subprocess.PIPE,
            ).stdout)

    def test_deferred_bundle_exports_standard_prediction(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            workspace, head = self._git_workspace(root)
            config_document = json.loads(ASTROPY_CONFIG.read_text(encoding="utf-8"))
            config_document["task"]["base_commit"] = head
            config_path = root / "astropy-config.json"
            config_path.write_text(json.dumps(config_document), encoding="utf-8")
            effective = runner.build_effective_config(
                config_path, interface="atomic", model="fake",
                output_root=root / "runs", episode_id="astropy-agent-test",
                workspace_source=workspace,
            )
            prompt = json.dumps(runner._prompt(effective), ensure_ascii=False)
            self.assertNotIn("cright[-right.shape", prompt)
            self.assertNotIn("official frozen dataset patch bytes", prompt)
            bundle = runner.run_episode(effective)
            functional = json.loads((bundle / "functional_oracle.json").read_text())
            self.assertEqual("DEFERRED", functional["status"])
            self.assertTrue(functional["official_swebench_harness"])

            prediction_path = root / "prediction.json"
            fixture_manifest = copy.deepcopy(self.manifest)
            fixture_manifest["task"]["base_commit"] = head
            record = swebench_agent.write_prediction(
                bundle, prediction_path, fixture_manifest
            )
            row = swebench_agent.validate_prediction(prediction_path, self.manifest)
            self.assertEqual("astropy__astropy-12907", row["instance_id"])
            self.assertIn("VALUE = 2", row["model_patch"])
            self.assertEqual("atomic", record["interface"])

    def test_agent_oracle_requires_resolved_and_exact_frozen_sets(self):
        oracle = self.manifest["task"]["oracle"]
        report = {
            "resolved": True,
            "tests_status": {
                "FAIL_TO_PASS": {"success": oracle["fail_to_pass"], "failure": []},
                "PASS_TO_PASS": {"success": oracle["pass_to_pass"], "failure": []},
            },
        }
        passed, errors = swebench_agent.agent_oracle_matches(report, self.manifest)
        self.assertTrue(passed, errors)
        report["resolved"] = False
        passed, errors = swebench_agent.agent_oracle_matches(report, self.manifest)
        self.assertFalse(passed)
        self.assertIn("official harness did not resolve the task", errors)


if __name__ == "__main__":
    unittest.main()

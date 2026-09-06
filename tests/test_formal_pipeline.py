from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from analysis.analyze_formal_matrix import analyze
from experiment.formal import build_formal_plan, run_formal_matrix
from experiment.permission import load_policy
from experiment.runner import load_config
from oracle.prepare_predictions import prepare


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs/experiment_action_boundary_formal.yaml"
PERMISSION_PATH = ROOT / "configs/permission.yaml"


class FormalPlanTests(unittest.TestCase):
    def setUp(self):
        self.config = load_config(CONFIG_PATH)

    def test_full_matrix_is_interleaved_and_duplicate_free(self):
        plan, tasks, _ = build_formal_plan(self.config, ROOT)
        self.assertEqual(54, len(plan))
        self.assertEqual(3, len(tasks))
        self.assertEqual(54, len({item.run_id for item in plan}))
        self.assertEqual(
            [
                "pallets__flask-5014-G1-clean-r1",
                "pallets__flask-5014-G2-clean-r1",
                "pallets__flask-5014-G4-clean-r1",
                "pallets__flask-5014-G1-attack01-r1",
                "pallets__flask-5014-G2-attack01-r1",
                "pallets__flask-5014-G4-attack01-r1",
            ],
            [item.run_id for item in plan[:6]],
        )
        self.assertEqual([1, 2, 3], sorted({item.rollout for item in plan}))

    def test_formal_config_freezes_capacity_and_budget(self):
        self.assertEqual({"G1": 1, "G2": 2, "G4": 4}, {
            name: self.config["granularity"][name]["max_ops_per_action"]
            for name in ("G1", "G2", "G4")
        })
        self.assertEqual([1, 2, 3], self.config["rollouts"])
        self.assertEqual(50, self.config["budget"]["max_model_actions"])
        self.assertEqual(100, self.config["budget"]["max_backend_operations"])
        self.assertEqual(1800, self.config["budget"]["timeout_seconds"])
        self.assertEqual(3, self.config["server"]["max_num_seqs"])


class FormalDryRunTests(unittest.TestCase):
    def test_dry_run_isolated_matrix_and_resume(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "formal"
            config = load_config(CONFIG_PATH)
            results = run_formal_matrix(
                config,
                load_policy(PERMISSION_PATH),
                output,
                ROOT,
                CONFIG_PATH,
                PERMISSION_PATH,
                parallel=3,
                dry_run=True,
                task_filter="pallets__flask-5014",
            )
            self.assertEqual(18, len(results))
            self.assertTrue(all(row["status"] == "completed" for row in results))
            self.assertEqual(18, len(list((output / "runs").iterdir())))
            clean = json.loads((output / "runs" / "pallets__flask-5014-G1-clean-r1" / "result.json").read_text())
            attack = json.loads((output / "runs" / "pallets__flask-5014-G1-attack01-r1" / "result.json").read_text())
            self.assertIsNone(clean["attack_metadata"])
            self.assertEqual("repository_comment_hijack_v1", attack["attack_metadata"]["attack_id"])
            self.assertIn(attack["worker_slot"], {1, 2, 3})
            attack_metadata = {
                json.dumps(json.loads((output / "runs" / f"pallets__flask-5014-{granularity}-attack01-r1" / "result.json").read_text())["attack_metadata"], sort_keys=True)
                for granularity in ("G1", "G2", "G4")
            }
            self.assertEqual(1, len(attack_metadata))

            incomplete = output / "runs" / "pallets__flask-5014-G2-clean-r1" / "COMPLETE.json"
            incomplete.unlink()
            resumed = run_formal_matrix(
                config,
                load_policy(PERMISSION_PATH),
                output,
                ROOT,
                CONFIG_PATH,
                PERMISSION_PATH,
                parallel=3,
                resume=True,
                dry_run=True,
                task_filter="pallets__flask-5014",
            )
            self.assertEqual(18, len(resumed))
            self.assertTrue(all(row["status"] == "completed" for row in resumed))
            self.assertTrue(list((output / "incomplete_attempts").iterdir()))

            rows, summaries = analyze(output)
            self.assertEqual(18, len(rows))
            self.assertEqual(6, len(summaries))
            self.assertEqual({"G1", "G2", "G4"}, {row["G"] for row in rows})

    def test_parallel_limit_is_three(self):
        with tempfile.TemporaryDirectory() as temporary:
            config = load_config(CONFIG_PATH)
            with self.assertRaises(ValueError):
                run_formal_matrix(
                    config, load_policy(PERMISSION_PATH), Path(temporary) / "formal", ROOT,
                    CONFIG_PATH, PERMISSION_PATH, parallel=4, dry_run=True,
                    task_filter="pallets__flask-5014",
                )

    def test_worker_exception_isolated_from_other_runs(self):
        def fake_run_one(task, interface_name, condition, seed, config, permission, model, output_dir, **kwargs):
            if interface_name == "G1":
                raise RuntimeError("synthetic worker failure")
            output_dir.mkdir(parents=True, exist_ok=False)
            (output_dir / "trajectory.jsonl").write_text("", encoding="utf-8")
            return {"task_id": task.instance_id, "final_patch": "", "attack_metadata": None}

        with tempfile.TemporaryDirectory() as temporary, patch("experiment.formal.run_one", side_effect=fake_run_one):
            config = load_config(CONFIG_PATH)
            results = run_formal_matrix(
                config, load_policy(PERMISSION_PATH), Path(temporary) / "formal", ROOT,
                CONFIG_PATH, PERMISSION_PATH, parallel=3, dry_run=True,
                task_filter="pallets__flask-5014",
            )
            self.assertEqual(6, sum(row["status"] == "incomplete" for row in results))
            self.assertEqual(12, sum(row["status"] == "completed" for row in results))


class FreezeAndOracleTests(unittest.TestCase):
    def _dry_root(self, temporary: str) -> Path:
        root = Path(temporary) / "formal"
        config = load_config(CONFIG_PATH)
        run_formal_matrix(
            config, load_policy(PERMISSION_PATH), root, ROOT,
            CONFIG_PATH, PERMISSION_PATH, parallel=3, dry_run=True,
            task_filter="pallets__flask-5014",
        )
        return root

    def test_freeze_creates_provenance_and_hashes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self._dry_root(temporary)
            destination = Path(temporary) / "drive"
            subprocess.run([
                sys.executable, str(ROOT / "scripts/freeze_experiment.py"), str(root),
                "--destination", str(destination),
            ], check=True, capture_output=True, text=True)
            frozen = destination / root.name
            for name in ("PLAN.json", "RUN_MANIFEST.json", "PROVENANCE.txt", "GIT_STATUS.txt", "SHA256SUMS", "RUNTIME_METADATA.json"):
                self.assertTrue((frozen / name).is_file(), name)
            self.assertIn("result.json", (frozen / "SHA256SUMS").read_text())

    def test_prediction_preparation_handles_empty_patch_and_duplicates(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self._dry_root(temporary)
            destination, manifest = prepare(
                root, "pallets__flask-5014-G1-clean-r1", None,
            )
            self.assertTrue(destination.is_file())
            self.assertEqual("not_attempted_empty_patch", manifest[0]["evaluator_status"])
            directory, all_manifest = prepare(root, None, None)
            self.assertTrue(directory.is_dir())
            self.assertEqual(18, len(all_manifest))
            self.assertEqual(18, len(list(directory.glob("*.jsonl"))))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from oracle.adapter import (
    evaluate_run,
    load_run,
    load_runs,
    parse_official_outputs,
    prepare_predictions,
    run_official,
    summarize_experiment,
)


class OracleAdapterTests(unittest.TestCase):
    def _write_json(self, path: Path, value: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")

    def _formal_root(self, temporary: str) -> Path:
        root = Path(temporary) / "formal"
        specs = []
        for granularity, capacity in (("G1", 1), ("G2", 2), ("G4", 4)):
            for rollout in (1, 2, 3):
                run_id = f"pallets__flask-5014-{granularity}-clean-r{rollout}"
                specs.append({
                    "run_id": run_id,
                    "task_id": "pallets__flask-5014",
                    "G": granularity,
                    "granularity_condition": granularity,
                    "max_ops_per_action": capacity,
                    "condition": "clean",
                    "rollout": rollout,
                })
        attack_id = "pallets__flask-5014-G2-attack01-r1"
        specs.append({
            "run_id": attack_id,
            "task_id": "pallets__flask-5014",
            "G": "G2",
            "granularity_condition": "G2",
            "max_ops_per_action": 2,
            "condition": "attack",
            "attack_id": "repository_comment_hijack_v1",
            "rollout": 1,
        })
        self._write_json(root / "PLAN.json", {"runs": specs})
        self._write_json(root / "experiment_metadata.json", {"experiment_id": "formal-test-v1"})
        self._write_json(root / "git_provenance.json", {"branch": "test", "commit": "abc"})
        for spec in specs:
            run_dir = root / "runs" / spec["run_id"]
            patch = "" if spec["run_id"].endswith("G4-clean-r2") else "diff --git a/a.py b/a.py\n"
            attack = None
            if spec["condition"] == "attack":
                attack = {
                    "attack_family": "repository_comment_hijack",
                    "attack_id": "repository_comment_hijack_v1",
                }
            self._write_json(run_dir / "result.json", {
                **spec,
                "task_id": spec["task_id"],
                "final_patch": patch,
                "attack_metadata": attack,
                "actions": 2,
                "backend_operations": 3 if spec["G"] != "G1" else 2,
                "input_tokens": 10,
                "output_tokens": 5,
                "runtime_seconds": 0.5,
                "attack_exposed": spec["condition"] == "attack",
                "attack_target_attempted": False,
                "attack_success": False,
            })
            self._write_json(run_dir / "metadata.json", {
                "run_id": spec["run_id"],
                "task_id": spec["task_id"],
                "G": spec["G"],
                "condition": spec["condition"],
                "rollout": spec["rollout"],
                "model": {"name": "test-model"},
                "attack_metadata": attack,
            })
            (run_dir / "patch.diff").write_text(patch, encoding="utf-8")
            (run_dir / "trajectory.jsonl").write_text(
                "\n".join([
                    json.dumps({"event": "model_response", "action_id": "1"}),
                    json.dumps({"event": "backend_operation", "status": "success"}),
                    json.dumps({"event": "interface_action", "status": "executed", "operations_executed": 2}),
                    json.dumps({"event": "model_response", "action_id": "2"}),
                    json.dumps({"event": "backend_operation", "status": "success"}),
                    json.dumps({"event": "interface_action", "status": "finish", "operations_executed": 0}),
                ]) + "\n",
                encoding="utf-8",
            )
            self._write_json(run_dir / "COMPLETE.json", {"run_id": spec["run_id"], "status": "completed"})
        self._write_json(root / "tasks" / "verified_tasks.json", [{"instance_id": "pallets__flask-5014"}])
        return root

    def test_formal_metadata_includes_all_granularities_conditions_and_rollouts(self):
        with tempfile.TemporaryDirectory() as temporary:
            runs = load_runs(self._formal_root(temporary))
            self.assertEqual(10, len(runs))
            self.assertEqual({"G1", "G2", "G4"}, {run.granularity_condition for run in runs})
            self.assertEqual({1, 2, 3}, {run.rollout for run in runs if run.condition == "clean"})
            attack = next(run for run in runs if run.condition == "attack")
            self.assertEqual("repository_comment_hijack", attack.attack_family)
            self.assertEqual("repository_comment_hijack_v1", attack.attack_id)
            self.assertEqual("diff --git a/a.py b/a.py\n", attack.patch)

    def test_prediction_files_are_keyed_by_run_not_instance(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self._formal_root(temporary)
            destination, manifest = prepare_predictions(root)
            self.assertTrue(destination.is_dir())
            self.assertEqual(10, len(manifest))
            files = sorted(destination.glob("*.jsonl"))
            self.assertEqual(10, len(files))
            self.assertFalse((destination / "pallets__flask-5014-G4-clean-r2.jsonl").read_text())
            self.assertIn("pallets__flask-5014-G1-clean-r1.jsonl", {path.name for path in files})
            self.assertEqual("pallets__flask-5014", json.loads(files[0].read_text())["instance_id"])

    def test_empty_patch_is_not_attempted_and_summary_counts_it_as_agent_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self._formal_root(temporary)
            run = next(item for item in load_runs(root) if item.patch == "")
            row = evaluate_run(run, Path(temporary) / "oracle", Path(temporary) / "tasks.json", max_attempts=1)
            self.assertFalse(row["evaluation_attempted"])
            self.assertEqual("not_attempted_empty_patch", row["evaluation_status"])
            self.assertIsNone(row["resolved"])
            oracle = Path(temporary) / "oracle"
            oracle.mkdir(parents=True, exist_ok=True)
            (oracle / "oracle_results.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
            combined, summaries = summarize_experiment(root, oracle, output_root=oracle)
            self.assertEqual(10, len(combined))
            g4 = next(item for item in summaries if item["treatment"] == "G4" and item["condition"] == "clean")
            self.assertEqual(1, g4["empty_patches"])
            self.assertEqual(0, g4["resolved"])
            self.assertEqual(0.0, g4["agent_level_resolution_rate"])

    def test_official_report_is_authoritative_and_patch_failure_is_not_infrastructure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self._formal_root(temporary)
            run = next(item for item in load_runs(root) if item.patch)
            report = Path(temporary) / "report.json"
            report.write_text(json.dumps({run.instance_id: {
                "patch_successfully_applied": False,
                "resolved": False,
                "infra_failure": False,
            }}), encoding="utf-8")
            parsed = parse_official_outputs(report, None, run.instance_id)
            self.assertFalse(parsed["infrastructure_failure"])
            self.assertFalse(parsed["patch_applied"])
            self.assertFalse(parsed["resolved"])

    def test_infrastructure_failure_retries_finitely_and_is_separate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self._formal_root(temporary)
            run = next(item for item in load_runs(root) if item.patch)
            output = Path(temporary) / "oracle"
            calls = []

            def fake_runner(command, log_path, cwd):
                calls.append(command)
                official_id = command[command.index("-r") + 1]
                if len(calls) == 1:
                    result_dir = cwd / "logs" / "evaluation" / official_id
                    self._write_json(result_dir / "results.json", {"error_ids": [run.instance_id]})
                else:
                    report_dir = cwd / "logs" / "evaluation" / official_id / "model" / run.instance_id
                    self._write_json(report_dir / "report.json", {run.instance_id: {
                        "patch_successfully_applied": True,
                        "resolved": True,
                        "infra_failure": False,
                    }})
                return 0

            row = evaluate_run(
                run, output, Path(temporary) / "tasks.json",
                max_attempts=2, command_runner=fake_runner,
            )
            self.assertEqual(2, len(calls))
            self.assertEqual(1, row["retry_count"])
            self.assertFalse(row["infrastructure_failure"])
            self.assertTrue(row["resolved"])

    def test_historical_atomic_and_rp_artifacts_remain_legacy(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "legacy" / "input" / "runs" / "task-atomic-clean-1"
            patch = "diff --git a/a.py b/a.py\n"
            self._write_json(root / "result.json", {
                "task_id": "task-1", "interface": "atomic", "condition": "clean", "seed": 1,
                "final_patch": patch,
            })
            (root / "prediction.jsonl").write_text(json.dumps({
                "instance_id": "task-1", "model_patch": patch,
            }) + "\n", encoding="utf-8")
            (root / "trajectory.jsonl").write_text("", encoding="utf-8")
            run = load_runs(Path(temporary) / "legacy")[0]
            self.assertEqual("atomic", run.treatment)
            self.assertIsNone(run.granularity_condition)
            self.assertIsNone(run.max_ops_per_action)
            self.assertEqual(1, run.rollout)

    def test_run_official_and_combined_csv_use_one_row_per_formal_rollout(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self._formal_root(temporary)
            output = Path(temporary) / "oracle"
            task_metadata = Path(temporary) / "verified.json"
            task_metadata.write_text("[]\n", encoding="utf-8")

            def fake_runner(command, log_path, cwd):
                official_id = command[command.index("-r") + 1]
                instance_id = command[command.index("-i") + 1]
                report_dir = cwd / "logs" / "evaluation" / official_id / "model" / instance_id
                self._write_json(report_dir / "report.json", {instance_id: {
                    "patch_successfully_applied": True,
                    "resolved": True,
                    "infra_failure": False,
                }})
                return 0

            rows = run_official(
                root, output, task_metadata=task_metadata,
                max_attempts=1, command_runner=fake_runner,
            )
            self.assertEqual(10, len(rows))
            self.assertEqual(9, sum(row["evaluation_attempted"] for row in rows))
            combined, summaries = summarize_experiment(root, output, output_root=output)
            self.assertEqual(10, len(combined))
            self.assertEqual({"G1", "G2", "G4"}, {row["granularity_condition"] for row in combined})
            self.assertTrue((output / "rollout_oracle_combined.csv").is_file())
            self.assertTrue(any(row["condition"] == "attack" for row in summaries))


if __name__ == "__main__":
    unittest.main()
